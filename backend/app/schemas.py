from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    brand: str
    description: str
    price: Decimal
    stock: int
    image_url: str
    specs: dict[str, Any]
    featured: bool


class CartChange(BaseModel):
    product_id: int
    quantity: int = Field(ge=0, le=50)


class CartLine(BaseModel):
    product: ProductOut
    quantity: int
    subtotal: Decimal


class CartOut(BaseModel):
    items: list[CartLine]
    total: Decimal


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class AgentResponse(BaseModel):
    answer: str
    mode: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    products: list[ProductOut] = Field(default_factory=list)


class OrderItemOut(BaseModel):
    product_name: str
    unit_price: Decimal
    quantity: int


class OrderOut(BaseModel):
    id: int
    status: str
    payment_status: str
    currency: str
    total: Decimal
    created_at: datetime
    items: list[OrderItemOut]


class CheckoutOut(BaseModel):
    order_id: int
    paypal_order_id: str
    approval_url: str
    status: str
    currency: str
    total: Decimal


class CaptureOut(BaseModel):
    order_id: int
    payment_status: str
    paypal_status: str
    transaction_id: str | None
