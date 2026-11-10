import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Conversation
from app.services.cart_service import change_cart
from app.services.order_service import list_customer_orders
from app.services.product_service import compare_products, search_products
from app.services.recommendation_service import rank_products
from app.services.product_service import product_dict


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search the live product catalogue with optional category, keyword and maximum price filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "category": {"type": "string"},
                    "max_price": {"type": "number"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_products",
            "description": "Compare up to four real catalogue products by their current price, specifications and availability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_ids": {"type": "array", "items": {"type": "integer"}}
                },
                "required": ["product_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_product",
            "description": "Rank available products against the customer's needs and maximum budget. Never recommend above budget.",
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": {"type": "number"},
                    "keywords": {"type": "string"},
                    "category": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_cart",
            "description": "Set a product's cart quantity; quantity zero removes the item. Prices and stock are checked by the server.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer"},
                    "quantity": {"type": "integer", "minimum": 0, "maximum": 50},
                },
                "required": ["product_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Get the latest actual order and payment status for this customer.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "payment_assistance",
            "description": "Explain the PayPal checkout workflow and whether Sandbox is configured. This tool cannot approve or capture a payment.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _tool_result(
    name: str, args: dict[str, Any], db: Session, customer_id: str
) -> tuple[dict[str, Any], list[dict]]:
    if name == "search_products":
        products = search_products(
            db,
            query=str(args.get("query", ""))[:200],
            category=str(args["category"])[:60] if args.get("category") else None,
            max_price=Decimal(str(args["max_price"])) if args.get("max_price") is not None else None,
        )
        values = [product_dict(product) for product in products]
        return {"products": values, "count": len(values)}, values
    if name == "compare_products":
        ids = args.get("product_ids", [])
        if not isinstance(ids, list) or not all(type(value) is int for value in ids):
            raise ValueError("product_ids must be an array of integers")
        values = compare_products(db, ids)
        return {"products": values, "count": len(values)}, values
    if name == "recommend_product":
        budget = Decimal(str(args["budget"])) if args.get("budget") is not None else None
        category = str(args["category"])[:60] if args.get("category") else None
        products = search_products(db, category=category, max_price=budget, limit=100)
        ranked = rank_products(products, budget, str(args.get("keywords", ""))[:300])
        values = [
            {**product_dict(product), "reason": reason}
            for product, reason in ranked[:5]
        ]
        return {"recommendations": values, "count": len(values)}, values
    if name == "manage_cart":
        product_id, quantity = args.get("product_id"), args.get("quantity")
        if type(product_id) is not int or type(quantity) is not int or not 0 <= quantity <= 50:
            raise ValueError("product_id and quantity must be valid integers")
        items, total = change_cart(db, customer_id, product_id, quantity)
        return {
            "cart": [
                {
                    "product": product_dict(item.product),
                    "quantity": item.quantity,
                    "subtotal": str(item.product.price * item.quantity),
                }
                for item in items
            ],
            "total": str(total),
        }, []
    if name == "get_order_status":
        orders = list_customer_orders(db, customer_id)
        return {
            "orders": [
                {
                    "id": order.id,
                    "status": order.status,
                    "payment_status": order.payment_status,
                    "total": str(order.total),
                    "currency": order.currency,
                }
                for order in orders[:10]
            ]
        }, []
    if name == "payment_assistance":
        configured = settings.paypal_configured
        return {
            "paypal_sandbox_configured": configured,
            "message": (
                "Customer must review the order and approve on PayPal. The backend captures only after approval."
                if configured
                else "PayPal is not configured. Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET to enable Sandbox checkout."
            ),
        }, []
    raise ValueError(f"Unsupported tool: {name}")


def _fallback(db: Session, message: str) -> tuple[str, list[dict]]:
    budget = None
    matches = re.search(
        r"(?:under|below|less than|max(?:imum)?|budget(?: of)?|within)\s*(?:₹|rs\.?|inr|\$)?\s*([\d,]+(?:\.\d{1,2})?)|(?:₹|\$)\s*([\d,]+(?:\.\d{1,2})?)",
        message,
        re.IGNORECASE,
    )
    if matches:
        raw = next((value for value in matches.groups() if value), None)
        if raw:
            try:
                budget = Decimal(raw.replace(",", ""))
            except InvalidOperation:
                budget = None
    categories = {
        "laptop": "Laptops",
        "computer": "Laptops",
        "phone": "Phones",
        "mobile": "Phones",
        "headphone": "Audio",
        "earbud": "Audio",
        "tablet": "Tablets",
        "monitor": "Monitors",
        "watch": "Wearables",
        "mouse": "Accessories",
        "keyboard": "Accessories",
    }
    category = next((value for key, value in categories.items() if key in message.lower()), None)
    products = search_products(db, category=category, max_price=budget, limit=8)
    if products:
        results = [product_dict(product) for product in products]
        return (
            "Fallback catalogue mode (not AI-generated): here are matching in-stock products. "
            "Prices are shown in the catalogue currency; refine with a category or budget.",
            results,
        )
    return (
        "Fallback catalogue mode (not AI-generated): I couldn't find an in-stock match. "
        "Try a broader category or a different budget.",
        [],
    )


def run_agent(db: Session, customer_id: str, message: str) -> dict:
    db.add(Conversation(customer_id=customer_id, role="user", content=message))
    db.commit()
    if not settings.groq_api_key:
        answer, products = _fallback(db, message)
        db.add(Conversation(customer_id=customer_id, role="assistant", content=answer))
        db.commit()
        return {"answer": answer, "mode": "fallback", "tool_calls": [], "products": products}

    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "You are TrustCart AI, a shopping assistant. Use only tool results for catalogue, "
                "stock, cart and order facts. Do not invent prices, availability or payment status. "
                "Respect a stated budget strictly. Never approve or capture payments. The customer "
                "must approve checkout through PayPal."
            ),
        },
        {"role": "user", "content": message},
    ]
    calls: list[dict] = []
    shown_products: list[dict] = []
    try:
        with httpx.Client(timeout=30.0) as client:
            for _ in range(4):
                response = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    json={
                        "model": settings.groq_model,
                        "messages": messages,
                        "tools": TOOL_DEFINITIONS,
                        "tool_choice": "auto",
                        "temperature": 0.2,
                    },
                )
                response.raise_for_status()
                choice = response.json()["choices"][0]["message"]
                messages.append(choice)
                tool_calls = choice.get("tool_calls") or []
                if not tool_calls:
                    answer = choice.get("content") or "I couldn't produce a response. Please try again."
                    db.add(Conversation(customer_id=customer_id, role="assistant", content=answer))
                    db.commit()
                    return {
                        "answer": answer,
                        "mode": "groq",
                        "tool_calls": calls,
                        "products": shown_products,
                    }
                for tool_call in tool_calls:
                    function = tool_call["function"]
                    tool_name = function.get("name", "")
                    args = json.loads(function.get("arguments") or "{}")
                    result, products = _tool_result(tool_name, args, db, customer_id)
                    shown_products.extend(products)
                    calls.append({"name": tool_name, "arguments": args, "result": result})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": tool_name,
                            "content": json.dumps(result, default=str),
                        }
                    )
        raise HTTPException(status_code=502, detail="AI tool call limit reached")
    except HTTPException:
        raise
    except httpx.HTTPError:
        answer, products = _fallback(db, message)
        answer = (
            "Fallback catalogue mode (not AI-generated): the Groq API is unavailable or "
            "misconfigured. " + answer.split(": ", 1)[-1]
        )
        db.add(Conversation(customer_id=customer_id, role="assistant", content=answer))
        db.commit()
        return {"answer": answer, "mode": "fallback", "tool_calls": calls, "products": products}
    except (KeyError, ValueError, TypeError, InvalidOperation) as exc:
        raise HTTPException(
            status_code=502,
            detail="Groq request or tool execution failed. Check the API key, model, and request before retrying.",
        ) from exc
