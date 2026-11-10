from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas import ProductOut
from app.services.product_service import search_products
from app.services.product_service import product_dict

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(
    q: str = "",
    category: str | None = None,
    max_price: Decimal | None = Query(default=None, gt=0),
    featured: bool | None = None,
    db: Session = Depends(get_db),
):
    products = search_products(db, q, category, max_price, 100)
    if featured is not None:
        products = [item for item in products if item.featured is featured]
    return [product_dict(item) for item in products]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_dict(product)
