import pytest
from pydantic import ValidationError

from apps.api.agents.tool_schemas import (
    GetUpsellCandidatesInput,
    GetUpsellCandidatesOutput,
    PriceOrderInput,
    PriceOrderOutput,
    SearchCatalogInput,
    SearchCatalogOutput,
)


def test_search_catalog_input_accepts_valid_query():
    value = SearchCatalogInput(
        query="gaming controller",
        category_hint="Controllers / Peripherals",
    )

    assert value.query == "gaming controller"
    assert value.category_hint == "Controllers / Peripherals"


def test_search_catalog_input_rejects_empty_query():
    with pytest.raises(ValidationError):
        SearchCatalogInput(query="")


def test_search_catalog_output_accepts_up_to_five_matches():
    output = SearchCatalogOutput(
        matches=[
            {
                "product_id": "PER-001",
                "name": "DualSense Wireless Controller",
                "price_paise": 599000,
                "currency": "INR",
                "in_stock": True,
            }
        ]
    )

    assert len(output.matches) == 1


def test_search_catalog_output_rejects_more_than_five_matches():
    match = {
        "product_id": "PER-001",
        "name": "DualSense Wireless Controller",
        "price_paise": 599000,
        "currency": "INR",
        "in_stock": True,
    }

    with pytest.raises(ValidationError):
        SearchCatalogOutput(matches=[match] * 6)


def test_upsell_input_requires_product_id():
    with pytest.raises(ValidationError):
        GetUpsellCandidatesInput(product_id="")


def test_upsell_output_accepts_valid_candidate():
    output = GetUpsellCandidatesOutput(
        candidates=[
            {
                "product_id": "MER-002",
                "name": "Genshin Impact Vision Keychain - Pyro Edition",
                "price_paise": 89900,
                "reason_code": "frequently_bought_with",
                "max_autonomous": True,
            }
        ]
    )

    assert output.candidates[0].product_id == "MER-002"
    assert output.candidates[0].max_autonomous is True


def test_price_order_input_accepts_positive_quantities():
    value = PriceOrderInput(
        line_items=[
            {
                "product_id": "GAME-001",
                "qty": 1,
            }
        ]
    )

    assert value.line_items[0].qty == 1


def test_price_order_input_rejects_zero_quantity():
    with pytest.raises(ValidationError):
        PriceOrderInput(
            line_items=[
                {
                    "product_id": "GAME-001",
                    "qty": 0,
                }
            ]
        )


def test_price_order_input_rejects_empty_line_items():
    with pytest.raises(ValidationError):
        PriceOrderInput(line_items=[])


def test_price_order_output_accepts_valid_result():
    output = PriceOrderOutput(
        amount_paise=89900,
        currency="INR",
        breakdown=[
            {
                "product_id": "MER-002",
                "name": "Genshin Impact Vision Keychain - Pyro Edition",
                "qty": 1,
                "unit_price_paise": 89900,
                "line_total_paise": 89900,
            }
        ],
    )

    assert output.amount_paise == 89900
    assert output.currency == "INR"