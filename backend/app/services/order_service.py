from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import CartItem, Order, OrderItem, Product


def create_order_from_cart(db: Session, customer_id: str) -> Order:
    cart_items = list(
        db.scalars(
            select(CartItem)
            .options(joinedload(CartItem.product))
            .where(CartItem.customer_id == customer_id)
        )
    )
    if not cart_items:
        raise HTTPException(status_code=400, detail="Your cart is empty")
    for item in cart_items:
        if item.quantity < 1 or item.quantity > item.product.stock:
            raise HTTPException(
                status_code=409, detail=f"Insufficient stock for {item.product.name}"
            )
    total = sum(
        (item.product.price * item.quantity for item in cart_items), Decimal("0.00")
    )
    order = Order(
        customer_id=customer_id,
        status="pending",
        payment_status="unpaid",
        currency=settings.paypal_currency,
        total=total,
    )
    order.items = [
        OrderItem(
            product_id=item.product_id,
            product_name=item.product.name,
            unit_price=item.product.price,
            quantity=item.quantity,
        )
        for item in cart_items
    ]
    db.add(order)
    db.flush()
    db.commit()
    db.refresh(order)
    return order


def get_customer_order(db: Session, customer_id: str, order_id: int) -> Order:
    order = db.scalars(
        select(Order)
        .options(joinedload(Order.items))
        .where(Order.customer_id == customer_id, Order.id == order_id)
    ).unique().one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def list_customer_orders(db: Session, customer_id: str) -> list[Order]:
    return list(
        db.scalars(
            select(Order)
            .options(joinedload(Order.items))
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
        ).unique()
    )


def validate_stock_for_order(db: Session, order: Order) -> None:
    for item in order.items:
        product = db.scalar(select(Product).where(Product.id == item.product_id).with_for_update())
        if not product or product.stock < item.quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock to complete order item {item.product_name}",
            )


def mark_order_paid(db: Session, order: Order) -> None:
    validate_stock_for_order(db, order)
    for item in order.items:
        product = db.get(Product, item.product_id)
        product.stock -= item.quantity
        cart_item = db.scalar(
            select(CartItem).where(
                CartItem.customer_id == order.customer_id,
                CartItem.product_id == item.product_id,
            )
        )
        if cart_item:
            if cart_item.quantity > item.quantity:
                cart_item.quantity -= item.quantity
            else:
                db.delete(cart_item)
    order.payment_status = "paid"
    order.status = "processing"
