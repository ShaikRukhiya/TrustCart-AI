from decimal import Decimal

import httpx
from fastapi import HTTPException

from app.config import settings


class PayPalService:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=15.0)

    def _require_config(self) -> None:
        if not settings.paypal_configured:
            raise HTTPException(
                status_code=503,
                detail="PayPal Sandbox is not configured. Add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET.",
            )

    def _access_token(self) -> str:
        self._require_config()
        response = self.client.post(
            f"{settings.paypal_base_url}/v1/oauth2/token",
            auth=(settings.paypal_client_id, settings.paypal_client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
        )
        if response.is_error:
            raise HTTPException(status_code=502, detail="PayPal authentication failed")
        try:
            return response.json()["access_token"]
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=502, detail="Invalid PayPal authentication response") from exc

    def _request(self, method: str, path: str, payload: dict | None = None, request_id: str | None = None):
        headers = {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        response = self.client.request(
            method,
            f"{settings.paypal_base_url}{path}",
            json=payload,
            headers=headers,
        )
        if response.is_error:
            raise HTTPException(status_code=502, detail="PayPal request failed")
        try:
            return response.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="Invalid PayPal response") from exc

    def create_order(self, local_order_id: int, total: Decimal, currency: str) -> dict:
        return self._request(
            "POST",
            "/v2/checkout/orders",
            {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": str(local_order_id),
                        "custom_id": str(local_order_id),
                        "amount": {"currency_code": currency, "value": f"{total:.2f}"},
                    }
                ],
                "application_context": {
                    "brand_name": "TrustCart AI",
                    "user_action": "PAY_NOW",
                    "return_url": f"{settings.frontend_origin}/checkout/return?order_id={local_order_id}",
                    "cancel_url": f"{settings.frontend_origin}/checkout/cancel?order_id={local_order_id}",
                },
            },
            request_id=f"trustcart-create-{local_order_id}",
        )

    def capture_order(self, paypal_order_id: str, local_order_id: int) -> dict:
        return self._request(
            "POST",
            f"/v2/checkout/orders/{paypal_order_id}/capture",
            {},
            request_id=f"trustcart-capture-{local_order_id}",
        )

    def get_order(self, paypal_order_id: str) -> dict:
        return self._request("GET", f"/v2/checkout/orders/{paypal_order_id}")


paypal_service = PayPalService()
