from decimal import Decimal

from app.models import Product


def rank_products(
    products: list[Product],
    budget: Decimal | None = None,
    keywords: str = "",
) -> list[tuple[Product, str]]:
    terms = {term.lower() for term in keywords.split() if len(term) > 2}
    ranked: list[tuple[float, Product, str]] = []
    for product in products:
        if budget is not None and product.price > budget:
            continue
        text = f"{product.name} {product.category} {product.description} {product.specs_json}".lower()
        matches = sum(term in text for term in terms)
        affordability = 0.0 if budget is None or budget == 0 else float((budget - product.price) / budget)
        score = matches + affordability * 0.35 + (0.1 if product.featured else 0)
        reason = "Matches your stated interests"
        if budget is not None:
            reason += f" and is within your {budget} budget"
        if matches == 0 and terms:
            reason = "Within budget and available in the catalogue"
        ranked.append((score, product, reason))
    ranked.sort(key=lambda result: (-result[0], result[1].price))
    return [(product, reason) for _, product, reason in ranked]
