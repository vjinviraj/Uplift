import pytest
from pydantic import ValidationError

from apps.api.agents.schemas import (
    MerchantAgentProposal,
    PurchaseRequest,
    UpsellProposal,
)


def test_purchase_request_accepts_valid_request():
    request = PurchaseRequest(
        query="gaming controller",
        budget_paise=250000,
        category_hint="Controllers / Peripherals",
        platform_hint="PlayStation",
        franchise_hint="",
    )

    assert request.query == "gaming controller"
    assert request.budget_paise == 250000
    assert request.category_hint == "Controllers / Peripherals"


def test_purchase_request_requires_query():
    with pytest.raises(ValidationError):
        PurchaseRequest(query="")


def test_purchase_request_rejects_negative_budget():
    with pytest.raises(ValidationError):
        PurchaseRequest(
            query="gaming controller",
            budget_paise=-1,
        )


def test_purchase_request_allows_optional_fields_to_be_omitted():
    request = PurchaseRequest(query="Genshin Impact")

    assert request.query == "Genshin Impact"
    assert request.budget_paise is None
    assert request.category_hint is None
    assert request.platform_hint is None
    assert request.franchise_hint is None


def test_upsell_proposal_accepts_valid_data():
    proposal = UpsellProposal(
        product_id="MER-002",
        reason="Low-cost Genshin merchandise.",
    )

    assert proposal.product_id == "MER-002"
    assert proposal.reason == "Low-cost Genshin merchandise."


def test_upsell_proposal_requires_product_id():
    with pytest.raises(ValidationError):
        UpsellProposal(
            product_id="",
            reason="Relevant item.",
        )


def test_upsell_proposal_requires_reason():
    with pytest.raises(ValidationError):
        UpsellProposal(
            product_id="MER-002",
            reason="",
        )


def test_merchant_agent_proposal_allows_no_upsell():
    proposal = MerchantAgentProposal(
        product_id="GAME-001",
    )

    assert proposal.product_id == "GAME-001"
    assert proposal.upsell is None


def test_merchant_agent_proposal_accepts_one_upsell():
    proposal = MerchantAgentProposal(
        product_id="GAME-001",
        upsell=UpsellProposal(
            product_id="MER-002",
            reason="Relevant low-cost merchandise.",
        ),
    )

    assert proposal.product_id == "GAME-001"
    assert proposal.upsell is not None
    assert proposal.upsell.product_id == "MER-002"


def test_merchant_agent_proposal_requires_product_id():
    with pytest.raises(ValidationError):
        MerchantAgentProposal(
            product_id="",
        )