from sqlmodel import Session, select

from apps.api.models import Product
from apps.api.models import CompatibilityMap


def _score_product(
    product: Product,
    query: str,
) -> int:
    """Return a deterministic relevance score for a catalog product."""

    query_lower = query.lower()
    name_lower = product.name.lower()
    description_lower = product.description.lower()

    score = 0

    # Exact product-name match.
    if query_lower == name_lower:
        score += 100

    # Complete query appears in the product name.
    if query_lower in name_lower:
        score += 50

    # Individual query terms.
    for term in query_lower.split():
        if term in name_lower:
            score += 20
        elif term in description_lower:
            score += 5

    # Prefer products that are actually available.
    if product.in_stock:
        score += 10

    return score


def search_catalog(
    session: Session,
    query: str,
    category_hint: str | None = None,
) -> dict:
    """
    Search the catalog and return up to five deterministically ranked matches.

    If category_hint is provided, it acts as a hard category constraint.

    The function is read-only and never modifies catalog data.
    """

    query = query.strip()

    if not query:
        raise ValueError("query must not be empty")

    statement = select(Product)

    # A supplied category hint is a hard constraint.
    if category_hint:
        statement = statement.where(
            Product.category == category_hint
        )

    products = session.exec(statement).all()

    query_terms = query.lower().split()

    matches = []

    for product in products:
        searchable_text = (
            f"{product.name} "
            f"{product.category} "
            f"{product.description}"
        ).lower()

        # At least one query term must match.
        # Ranking determines which matches are most relevant.
        if any(term in searchable_text for term in query_terms):
            matches.append(product)

    # Deterministic ranking:
    # 1. Higher relevance score first
    # 2. Product ID as deterministic tie-breaker
    matches.sort(
        key=lambda product: (
            -_score_product(product, query),
            product.id,
        )
    )

    # Contract: maximum five results.
    matches = matches[:5]

    return {
        "matches": [
            {
                "product_id": product.id,
                "name": product.name,
                "price_paise": product.price_paise,
                "currency": product.currency,
                "in_stock": product.in_stock,
            }
            for product in matches
        ]
    }

def get_upsell_candidates(
    session: Session,
    product_id: str,
) -> dict:
    """
    Return deterministic upsell candidates defined in CompatibilityMap.

    No compatibility or recommendation relationship is invented here.
    """

    mappings = session.exec(
        select(CompatibilityMap).where(
            CompatibilityMap.product_id == product_id
        )
    ).all()

    candidates = []

    for mapping in mappings:
        product = session.get(Product, mapping.upsell_product_id)

        # Ignore broken/stale mappings safely.
        if product is None:
            continue

        candidates.append(
            {
                "product_id": product.id,
                "name": product.name,
                "price_paise": product.price_paise,
                "reason_code": mapping.reason_code,
                "max_autonomous": mapping.max_autonomous,
            }
        )

    return {"candidates": candidates}

def price_order(
    session: Session,
    line_items: list[dict],
) -> dict:
    """
    Calculate the authoritative order total from current database prices.

    Prices supplied by callers are never trusted.
    """

    if not line_items:
        raise ValueError("line_items must not be empty")

    breakdown = []
    amount_paise = 0

    for line_item in line_items:
        product_id = line_item.get("product_id")
        qty = line_item.get("qty")

        if not product_id:
            raise ValueError("product_id is required")

        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("quantity must be a positive integer")

        product = session.get(Product, product_id)

        if product is None:
            raise ValueError(f"Product not found: {product_id}")

        if not product.in_stock:
            raise ValueError(f"Product is out of stock: {product_id}")

        # IMPORTANT:
        # The authoritative price comes from the database.
        unit_price_paise = product.price_paise
        line_total_paise = unit_price_paise * qty

        amount_paise += line_total_paise

        breakdown.append(
            {
                "product_id": product.id,
                "name": product.name,
                "qty": qty,
                "unit_price_paise": unit_price_paise,
                "line_total_paise": line_total_paise,
            }
        )

    return {
        "amount_paise": amount_paise,
        "currency": "INR",
        "breakdown": breakdown,
    }