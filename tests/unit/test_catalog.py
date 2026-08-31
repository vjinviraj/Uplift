from scripts.seed_catalog import (
    AUTONOMOUS_UPSELL_MAX_PAISE,
    COMPATIBILITY_MAP,
    PRODUCTS,
    VALID_REASON_CODES,
)


def test_catalog_has_exactly_30_products():
    assert len(PRODUCTS) == 30


def test_product_ids_are_unique():
    ids = [product["id"] for product in PRODUCTS]

    assert len(ids) == len(set(ids))


def test_product_names_are_unique():
    names = [product["name"] for product in PRODUCTS]

    assert len(names) == len(set(names))


def test_all_products_use_inr_and_integer_paise():
    for product in PRODUCTS:
        assert product["currency"] == "INR"
        assert isinstance(product["price_paise"], int)
        assert product["price_paise"] >= 0


def test_all_products_have_required_fields():
    required_fields = {
        "id",
        "name",
        "category",
        "price_paise",
        "currency",
        "in_stock",
        "description",
    }

    for product in PRODUCTS:
        assert required_fields.issubset(product.keys())


def test_relationship_references_exist():
    product_ids = {product["id"] for product in PRODUCTS}

    for mapping in COMPATIBILITY_MAP:
        assert mapping["product_id"] in product_ids
        assert mapping["upsell_product_id"] in product_ids


def test_relationship_reason_codes_are_valid():
    for mapping in COMPATIBILITY_MAP:
        assert mapping["reason_code"] in VALID_REASON_CODES


def test_autonomous_upsells_never_exceed_1000_rupees():
    products_by_id = {
        product["id"]: product
        for product in PRODUCTS
    }

    for mapping in COMPATIBILITY_MAP:
        if mapping["max_autonomous"]:
            target = products_by_id[mapping["upsell_product_id"]]

            assert target["price_paise"] <= AUTONOMOUS_UPSELL_MAX_PAISE