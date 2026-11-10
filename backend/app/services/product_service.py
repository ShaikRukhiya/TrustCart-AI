import json
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Product


def product_dict(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "brand": product.brand,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "image_url": product.image_url,
        "specs": json.loads(product.specs_json),
        "featured": product.featured,
    }


def search_products(
    db: Session,
    query: str = "",
    category: str | None = None,
    max_price: Decimal | None = None,
    limit: int = 20,
) -> list[Product]:
    statement = select(Product).where(Product.stock > 0)
    if category is None:
        category_aliases = {
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
        category = next(
            (value for token, value in category_aliases.items() if token in query.lower()),
            None,
        )
    if category:
        statement = statement.where(Product.category.ilike(f"%{category.strip()}%"))
    if max_price is not None:
        statement = statement.where(Product.price <= max_price)
    terms = [term for term in query.lower().split() if len(term) > 1]
    term_filters = []
    for term in terms[:8]:
        pattern = f"%{term}%"
        term_filters.append(
            or_(
                Product.name.ilike(pattern),
                Product.brand.ilike(pattern),
                Product.category.ilike(pattern),
                Product.description.ilike(pattern),
                Product.specs_json.ilike(pattern),
            )
        )
    if term_filters:
        statement = statement.where(or_(*term_filters))
    return list(db.scalars(statement.order_by(Product.featured.desc(), Product.id).limit(limit)))


def compare_products(db: Session, product_ids: list[int]) -> list[dict]:
    if not product_ids or len(product_ids) > 4:
        raise ValueError("Compare between one and four product IDs")
    products = list(db.scalars(select(Product).where(Product.id.in_(set(product_ids)))))
    by_id = {product.id: product for product in products}
    return [product_dict(by_id[pid]) for pid in product_ids if pid in by_id]
