from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import CartItem, Product


def get_cart(db: Session, customer_id: str) -> tuple[list[CartItem], Decimal]:
    items = list(
        db.scalars(
            select(CartItem)
            .options(joinedload(CartItem.product))
            .where(CartItem.customer_id == customer_id)
            .order_by(CartItem.id)
        )
    )
    total = sum((item.product.price * item.quantity for item in items), Decimal("0.00"))
    return items, total


def change_cart(
    db: Session, customer_id: str, product_id: int, quantity: int
) -> tuple[list[CartItem], Decimal]:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if quantity > product.stock:
        raise HTTPException(status_code=409, detail="Requested quantity exceeds available stock")
    item = db.scalar(
        select(CartItem).where(
            CartItem.customer_id == customer_id, CartItem.product_id == product_id
        )
    )
    if quantity == 0:
        if item:
            db.delete(item)
    elif item:
        item.quantity = quantity
    else:
        db.add(CartItem(customer_id=customer_id, product_id=product_id, quantity=quantity))
    db.commit()
    return get_cart(db, customer_id)
