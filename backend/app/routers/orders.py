from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Order, PaymentTransaction
from app.routers.cart import customer_id
from app.schemas import CaptureOut, CheckoutOut, OrderOut
from app.services.order_service import (
    create_order_from_cart,
    get_customer_order,
    list_customer_orders,
    mark_order_paid,
    validate_stock_for_order,
)
from app.services.paypal_service import paypal_service

router = APIRouter(prefix="/api", tags=["orders and payments"])


def paypal_amount(data: dict, order: Order) -> tuple[str, str, str | None]:
    try:
        unit = data["purchase_units"][0]
        capture = unit["payments"]["captures"][0]
        amount = capture["amount"]
        capture_id = capture["id"]
        status = capture["status"]
        value, currency = amount["value"], amount["currency_code"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="PayPal returned an incomplete capture response") from exc
    if currency != order.currency or value != f"{order.total:.2f}":
        raise HTTPException(status_code=502, detail="Captured amount does not match the order")
    return status, value, capture_id


@router.post("/checkout", response_model=CheckoutOut)
def checkout(db: Session = Depends(get_db), customer: str = Depends(customer_id)):
    order = create_order_from_cart(db, customer)
    try:
        result = paypal_service.create_order(order.id, order.total, order.currency)
    except HTTPException:
        order.status = "checkout_failed"
        db.commit()
        raise
    if result.get("status") != "CREATED":
        order.status = "checkout_failed"
        db.commit()
        raise HTTPException(status_code=502, detail="PayPal did not create an approval order")
    approval = next(
        (link["href"] for link in result.get("links", []) if link.get("rel") == "approve"),
        None,
    )
    if not approval or not result.get("id"):
        order.status = "checkout_failed"
        db.commit()
        raise HTTPException(status_code=502, detail="PayPal response is missing its approval link")
    order.paypal_order_id = result["id"]
    db.commit()
    return {
        "order_id": order.id,
        "paypal_order_id": result["id"],
        "approval_url": approval,
        "status": result["status"],
        "currency": order.currency,
        "total": order.total,
    }


@router.post("/payments/{paypal_order_id}/capture", response_model=CaptureOut)
def capture_payment(
    paypal_order_id: str,
    db: Session = Depends(get_db),
    customer: str = Depends(customer_id),
):
    order = db.scalars(
        select(Order)
        .options(joinedload(Order.items))
        .where(Order.customer_id == customer, Order.paypal_order_id == paypal_order_id)
    ).unique().one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="PayPal order not found")
    existing = db.scalar(
        select(PaymentTransaction).where(PaymentTransaction.order_id == order.id)
    )
    if order.payment_status == "paid" and existing:
        return {
            "order_id": order.id,
            "payment_status": order.payment_status,
            "paypal_status": existing.status,
            "transaction_id": existing.paypal_capture_id,
        }
    if existing and existing.status == "pending":
        result = paypal_service.get_order(paypal_order_id)
        if result.get("id") != paypal_order_id:
            raise HTTPException(status_code=502, detail="PayPal response does not match the requested order")
        if result.get("status") == "COMPLETED":
            status, _, capture_id = paypal_amount(result, order)
            if status == "COMPLETED" and capture_id:
                mark_order_paid(db, order)
                existing.status = "completed"
                existing.paypal_capture_id = capture_id
                db.commit()
                return {
                    "order_id": order.id,
                    "payment_status": order.payment_status,
                    "paypal_status": status,
                    "transaction_id": capture_id,
                }
        return {
            "order_id": order.id,
            "payment_status": order.payment_status,
            "paypal_status": str(result.get("status", "PENDING")),
            "transaction_id": existing.paypal_capture_id,
        }
    if order.status != "pending" or order.payment_status != "unpaid":
        raise HTTPException(status_code=409, detail="This order is not awaiting payment")
    validate_stock_for_order(db, order)
    result = paypal_service.capture_order(paypal_order_id, order.id)
    if result.get("id") != paypal_order_id:
        raise HTTPException(status_code=502, detail="PayPal response does not match the requested order")
    if result.get("status") not in {"COMPLETED", "PENDING"}:
        order.payment_status = "failed"
        order.status = "payment_failed"
        db.add(
            PaymentTransaction(
                order_id=order.id,
                status=str(result.get("status", "failed")).lower(),
                amount=order.total,
                currency=order.currency,
            )
        )
        db.commit()
        return {
            "order_id": order.id,
            "payment_status": order.payment_status,
            "paypal_status": str(result.get("status", "FAILED")),
            "transaction_id": None,
        }
    status, _, capture_id = paypal_amount(result, order)
    if status != "COMPLETED" or not capture_id:
        order.payment_status = "pending" if status == "PENDING" else "failed"
        order.status = "pending" if status == "PENDING" else "payment_failed"
        db.add(
            PaymentTransaction(
                order_id=order.id,
                paypal_capture_id=capture_id,
                status=status.lower(),
                amount=order.total,
                currency=order.currency,
            )
        )
        db.commit()
        return {
            "order_id": order.id,
            "payment_status": order.payment_status,
            "paypal_status": status,
            "transaction_id": capture_id,
        }
    mark_order_paid(db, order)
    db.add(
        PaymentTransaction(
            order_id=order.id,
            paypal_capture_id=capture_id,
            status="completed",
            amount=order.total,
            currency=order.currency,
        )
    )
    db.commit()
    return {
        "order_id": order.id,
        "payment_status": order.payment_status,
        "paypal_status": status,
        "transaction_id": capture_id,
    }


@router.post("/checkout/{order_id}/cancel")
def cancel_checkout(
    order_id: int,
    db: Session = Depends(get_db),
    customer: str = Depends(customer_id),
):
    order = get_customer_order(db, customer, order_id)
    if order.status != "pending" or order.payment_status != "unpaid":
        raise HTTPException(status_code=409, detail="Only pending unpaid orders can be cancelled")
    order.status = "cancelled"
    order.payment_status = "cancelled"
    db.commit()
    return {"order_id": order.id, "status": order.status, "payment_status": order.payment_status}


@router.get("/orders", response_model=list[OrderOut])
def orders(db: Session = Depends(get_db), customer: str = Depends(customer_id)):
    return list_customer_orders(db, customer)


@router.get("/orders/{order_id}", response_model=OrderOut)
def order_detail(
    order_id: int, db: Session = Depends(get_db), customer: str = Depends(customer_id)
):
    return get_customer_order(db, customer, order_id)
