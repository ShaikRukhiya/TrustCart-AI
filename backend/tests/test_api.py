import json
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.seed import seed_products
from app.config import settings
from app.routers import orders as orders_router


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    test_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    with test_session() as db:
        seed_products(db)

    def override_get_db():
        with test_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def test_catalogue_is_seeded_and_searchable(client):
    response = client.get("/api/products", params={"q": "laptop", "max_price": 700})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    assert all(item["category"] == "Laptops" for item in data)
    assert all(Decimal(item["price"]) <= 700 for item in data)
    assert client.get("/api/products").status_code == 200


def test_health_and_product_detail_endpoints(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    product = client.get("/api/products/1")
    assert product.status_code == 200
    assert product.json()["id"] == 1
    assert client.get("/api/products/999999").status_code == 404


@pytest.mark.parametrize(
    "origin",
    [
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
)
def test_vite_localhost_origins_pass_cors_preflight(client, origin):
    response = client.options(
        "/api/products",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-customer-id,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_rejects_non_local_origins(client):
    response = client.options(
        "/api/products",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400


def test_cart_revalidates_stock_and_calculates_server_total(client):
    product = client.get("/api/products").json()[0]
    response = client.put(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 2},
        headers={"X-Customer-Id": "test-customer"},
    )
    assert response.status_code == 200
    assert Decimal(response.json()["total"]) == Decimal(product["price"]) * 2
    assert client.get(
        "/api/cart", headers={"X-Customer-Id": "test-customer"}
    ).json()["total"] == response.json()["total"]
    overstock = client.put(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": product["stock"] + 1},
        headers={"X-Customer-Id": "test-customer"},
    )
    assert overstock.status_code == 409
    removed = client.put(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 0},
        headers={"X-Customer-Id": "test-customer"},
    )
    assert removed.status_code == 200
    assert removed.json()["items"] == []


def test_invalid_cart_and_chat_inputs_are_rejected(client):
    invalid_quantity = client.put(
        "/api/cart/items",
        json={"product_id": 1, "quantity": -1},
        headers={"X-Customer-Id": "invalid-input-test"},
    )
    assert invalid_quantity.status_code == 422
    assert client.post("/api/agent/chat", json={"message": ""}).status_code == 422


def test_agent_labels_fallback_and_returns_database_products(client):
    response = client.post(
        "/api/agent/chat",
        json={"message": "I need a laptop under 700 for Python coding"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "fallback"
    assert "not AI-generated" in data["answer"]
    assert data["products"]
    assert all(Decimal(item["price"]) <= 700 for item in data["products"])


def test_checkout_without_paypal_credentials_never_marks_order_paid(client):
    product = client.get("/api/products").json()[0]
    headers = {"X-Customer-Id": "checkout-test"}
    assert client.put(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    ).status_code == 200
    response = client.post("/api/checkout", headers=headers)
    assert response.status_code == 503
    orders = client.get("/api/orders", headers=headers).json()
    assert len(orders) == 1
    assert orders[0]["payment_status"] == "unpaid"
    assert orders[0]["status"] == "checkout_failed"
    assert client.get(f"/api/orders/{orders[0]['id']}", headers=headers).status_code == 200
    assert client.get(
        f"/api/orders/{orders[0]['id']}",
        headers={"X-Customer-Id": "different-customer"},
    ).status_code == 404


def test_groq_tool_calls_execute_against_the_real_test_catalogue(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_service.settings",
        SimpleNamespace(groq_api_key="test-key", groq_model=settings.groq_model, paypal_configured=False),
    )
    tool_calls = [
        {"id": "search-1", "type": "function", "function": {
            "name": "search_products",
            "arguments": json.dumps({"query": "laptop", "max_price": 700}),
        }},
        {"id": "compare-1", "type": "function", "function": {
            "name": "compare_products", "arguments": json.dumps({"product_ids": [1, 2]}),
        }},
        {"id": "recommend-1", "type": "function", "function": {
            "name": "recommend_product",
            "arguments": json.dumps({"budget": 700, "keywords": "Python coding", "category": "laptop"}),
        }},
        {"id": "cart-1", "type": "function", "function": {
            "name": "manage_cart", "arguments": json.dumps({"product_id": 1, "quantity": 1}),
        }},
        {"id": "status-1", "type": "function", "function": {
            "name": "get_order_status", "arguments": "{}",
        }},
        {"id": "payment-1", "type": "function", "function": {
            "name": "payment_assistance", "arguments": "{}",
        }},
    ]

    class FakeResponse:
        def __init__(self, message):
            self.message = message

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": self.message}]}

    class FakeGroqClient:
        def __init__(self, *args, **kwargs):
            self.calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            self.calls += 1
            message = (
                {"role": "assistant", "tool_calls": tool_calls}
                if self.calls == 1
                else {"role": "assistant", "content": "I checked the live catalogue and cart."}
            )
            return FakeResponse(message)

    monkeypatch.setattr("app.services.agent_service.httpx.Client", FakeGroqClient)
    response = client.post(
        "/api/agent/chat",
        json={"message": "Find and compare affordable laptops, add one to my cart"},
        headers={"X-Customer-Id": "agent-tool-test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "groq"
    assert {call["name"] for call in data["tool_calls"]} == {
        "search_products", "compare_products", "recommend_product",
        "manage_cart", "get_order_status", "payment_assistance",
    }
    recommendation_call = next(call for call in data["tool_calls"] if call["name"] == "recommend_product")
    assert all(Decimal(item["price"]) <= 700 for item in recommendation_call["result"]["recommendations"])
    cart = client.get("/api/cart", headers={"X-Customer-Id": "agent-tool-test"}).json()
    assert len(cart["items"]) == 1


def test_groq_transport_failure_returns_labeled_catalogue_fallback(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_service.settings",
        SimpleNamespace(groq_api_key="test-key", groq_model=settings.groq_model, paypal_configured=False),
    )

    class UnavailableGroqClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, *args, **kwargs):
            raise httpx.ConnectError("offline")

    monkeypatch.setattr("app.services.agent_service.httpx.Client", UnavailableGroqClient)
    response = client.post("/api/agent/chat", json={"message": "laptop under 700"})
    assert response.status_code == 200
    assert response.json()["mode"] == "fallback"
    assert "not AI-generated" in response.json()["answer"]
    assert response.json()["products"]


def test_pending_paypal_capture_is_not_paid_until_server_recheck(client, monkeypatch):
    headers = {"X-Customer-Id": "pending-payment-test"}
    product = client.get("/api/products").json()[0]
    client.put("/api/cart/items", json={"product_id": product["id"], "quantity": 1}, headers=headers)
    monkeypatch.setattr(
        orders_router.paypal_service,
        "create_order",
        lambda order_id, total, currency: {
            "id": "PAYPAL-ORDER-TEST",
            "status": "CREATED",
            "links": [{"rel": "approve", "href": "https://sandbox.example/approve"}],
        },
    )
    checkout = client.post("/api/checkout", headers=headers).json()
    capture = {
        "id": "PAYPAL-ORDER-TEST",
        "status": "PENDING",
        "purchase_units": [{"payments": {"captures": [{
            "id": "PAYPAL-CAPTURE-TEST",
            "status": "PENDING",
            "amount": {"currency_code": "USD", "value": f"{Decimal(product['price']):.2f}"},
        }]}}],
    }
    monkeypatch.setattr(orders_router.paypal_service, "capture_order", lambda *args: capture)
    pending = client.post(
        f"/api/payments/{checkout['paypal_order_id']}/capture", headers=headers
    )
    assert pending.status_code == 200
    assert pending.json()["payment_status"] == "pending"
    assert client.get("/api/orders", headers=headers).json()[0]["payment_status"] == "pending"

    verified = {
        **capture,
        "status": "COMPLETED",
        "purchase_units": [{"payments": {"captures": [{
            "id": "PAYPAL-CAPTURE-TEST",
            "status": "COMPLETED",
            "amount": {"currency_code": "USD", "value": f"{Decimal(product['price']):.2f}"},
        }]}}],
    }
    monkeypatch.setattr(orders_router.paypal_service, "get_order", lambda *args: verified)
    completed = client.post(
        f"/api/payments/{checkout['paypal_order_id']}/capture", headers=headers
    )
    assert completed.status_code == 200
    assert completed.json()["payment_status"] == "paid"
    assert completed.json()["transaction_id"] == "PAYPAL-CAPTURE-TEST"


def test_mocked_completed_capture_is_idempotent(client, monkeypatch):
    headers = {"X-Customer-Id": "idempotent-payment-test"}
    product = client.get("/api/products").json()[0]
    client.put(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    monkeypatch.setattr(
        orders_router.paypal_service,
        "create_order",
        lambda order_id, total, currency: {
            "id": "MOCK-IDEMPOTENT-ORDER",
            "status": "CREATED",
            "links": [{"rel": "approve", "href": "https://sandbox.example/approve"}],
        },
    )
    checkout = client.post("/api/checkout", headers=headers)
    assert checkout.status_code == 200

    calls = 0
    capture = {
        "id": "MOCK-IDEMPOTENT-ORDER",
        "status": "COMPLETED",
        "purchase_units": [{"payments": {"captures": [{
            "id": "MOCK-IDEMPOTENT-CAPTURE",
            "status": "COMPLETED",
            "amount": {
                "currency_code": "USD",
                "value": f"{Decimal(product['price']):.2f}",
            },
        }]}}],
    }

    def capture_order(*args):
        nonlocal calls
        calls += 1
        return capture

    monkeypatch.setattr(orders_router.paypal_service, "capture_order", capture_order)
    path = f"/api/payments/{checkout.json()['paypal_order_id']}/capture"
    first = client.post(path, headers=headers)
    second = client.post(path, headers=headers)

    assert first.status_code == 200
    assert first.json()["payment_status"] == "paid"
    assert second.status_code == 200
    assert second.json()["transaction_id"] == "MOCK-IDEMPOTENT-CAPTURE"
    assert calls == 1
    assert client.get(f"/api/products/{product['id']}").json()["stock"] == product["stock"] - 1


def test_capture_amount_mismatch_does_not_mark_order_paid(client, monkeypatch):
    headers = {"X-Customer-Id": "amount-mismatch-test"}
    product = client.get("/api/products").json()[0]
    client.put(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    monkeypatch.setattr(
        orders_router.paypal_service,
        "create_order",
        lambda order_id, total, currency: {
            "id": "MOCK-AMOUNT-ORDER",
            "status": "CREATED",
            "links": [{"rel": "approve", "href": "https://sandbox.example/approve"}],
        },
    )
    checkout = client.post("/api/checkout", headers=headers)
    assert checkout.status_code == 200
    monkeypatch.setattr(
        orders_router.paypal_service,
        "capture_order",
        lambda *args: {
            "id": "MOCK-AMOUNT-ORDER",
            "status": "COMPLETED",
            "purchase_units": [{"payments": {"captures": [{
                "id": "MOCK-WRONG-AMOUNT",
                "status": "COMPLETED",
                "amount": {"currency_code": "USD", "value": "0.01"},
            }]}}],
        },
    )

    response = client.post(
        f"/api/payments/{checkout.json()['paypal_order_id']}/capture",
        headers=headers,
    )
    assert response.status_code == 502
    assert client.get(
        f"/api/orders/{checkout.json()['order_id']}", headers=headers
    ).json()["payment_status"] == "unpaid"


def test_cancel_only_accepts_pending_unpaid_orders(client, monkeypatch):
    headers = {"X-Customer-Id": "cancel-pending-test"}
    product = client.get("/api/products").json()[0]
    client.put(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    monkeypatch.setattr(
        orders_router.paypal_service,
        "create_order",
        lambda order_id, total, currency: {
            "id": "MOCK-CANCEL-ORDER",
            "status": "CREATED",
            "links": [{"rel": "approve", "href": "https://sandbox.example/approve"}],
        },
    )
    checkout = client.post("/api/checkout", headers=headers)
    assert checkout.status_code == 200
    order_id = checkout.json()["order_id"]
    cancelled = client.post(f"/api/checkout/{order_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["payment_status"] == "cancelled"

    def fail_create_order(*args):
        raise HTTPException(status_code=503, detail="PayPal Sandbox is not configured")

    monkeypatch.setattr(
        orders_router.paypal_service, "create_order", fail_create_order
    )
    failed_headers = {"X-Customer-Id": "cancel-failed-checkout-test"}
    client.put(
        "/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=failed_headers,
    )
    failed_checkout = client.post("/api/checkout", headers=failed_headers)
    assert failed_checkout.status_code == 503
    failed_order_id = client.get("/api/orders", headers=failed_headers).json()[0]["id"]
    rejected = client.post(
        f"/api/checkout/{failed_order_id}/cancel", headers=failed_headers
    )
    assert rejected.status_code == 409
    assert client.get(
        f"/api/orders/{failed_order_id}", headers=failed_headers
    ).json()["status"] == "checkout_failed"
