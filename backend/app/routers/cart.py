from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CartChange, CartOut
from app.services.cart_service import change_cart, get_cart
from app.services.product_service import product_dict

router = APIRouter(prefix="/api/cart", tags=["cart"])


def customer_id(x_customer_id: str = Header(default="demo-customer")) -> str:
    value = x_customer_id.strip()
    if not value or len(value) > 80:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Invalid customer session")
    return value


def cart_response(db: Session, customer: str) -> dict:
    items, total = get_cart(db, customer)
    return {
        "items": [
            {
                "product": product_dict(item.product),
                "quantity": item.quantity,
                "subtotal": item.product.price * item.quantity,
            }
            for item in items
        ],
        "total": total,
    }


@router.get("", response_model=CartOut)
def read_cart(db: Session = Depends(get_db), customer: str = Depends(customer_id)):
    return cart_response(db, customer)


@router.put("/items", response_model=CartOut)
def update_cart(
    change: CartChange,
    db: Session = Depends(get_db),
    customer: str = Depends(customer_id),
):
    change_cart(db, customer, change.product_id, change.quantity)
    return cart_response(db, customer)
