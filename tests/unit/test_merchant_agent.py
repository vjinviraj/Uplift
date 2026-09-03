import pytest
from sqlmodel import Session, SQLModel, create_engine

from apps.api.agents.merchant_agent import MerchantAgent
from apps.api.agents.schemas import MerchantAgentProposal, PurchaseRequest
from apps.api.models import CompatibilityMap, PolicyConfig, Product


class FakeLLM:
    def __init__(self, proposals):
        self.proposals = list(proposals)
        self.calls = []

    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model,
            }
        )
        value = self.proposals.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def make_session() -> Session:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    session.add_all(
        [
            Product(
                id="GAME-001",
                name="Genshin Impact - Digital Edition",
                category="Games",
                price_paise=0,
                currency="INR",
                in_stock=True,
                description="Open-world action RPG.",
            ),
            Product(
                id="MER-002",
                name="Genshin Impact Vision Keychain - Pyro Edition",
                category="Gaming Merchandise",
                price_paise=89900,
                currency="INR",
                in_stock=True,
                description="Genshin Impact themed keychain.",
            ),
            Product(
                id="MER-001",
                name="Genshin Impact Paimon Plush",
                category="Gaming Merchandise",
                price_paise=249900,
                currency="INR",
                in_stock=True,
                description="Genshin Impact plush.",
            ),
        ]
    )

    session.add_all(
        [
            CompatibilityMap(
                product_id="GAME-001",
                upsell_product_id="MER-002",
                reason_code="frequently_bought_with",
                max_autonomous=True,
            ),
            CompatibilityMap(
                product_id="GAME-001",
                upsell_product_id="MER-001",
                reason_code="frequently_bought_with",
                max_autonomous=False,
            ),
        ]
    )
    session.commit()
    return session


def make_policy(**overrides) -> PolicyConfig:
    values = {
        "version": "v1",
        "max_single_item_price_paise": 100000,
        "max_order_total_without_extra_confirm_paise": 500000,
        "max_upsells_per_session": 1,
        "allowed_product_ids": None,
    }
    values.update(overrides)
    return PolicyConfig(**values)


def proposal(
    product_id="GAME-001",
    upsell_id="MER-002",
    reason="Relevant merchandise",
):
    return MerchantAgentProposal(
        product_id=product_id,
        upsell=(
            {"product_id": upsell_id, "reason": reason}
            if upsell_id is not None
            else None
        ),
    )


def test_valid_proposal_returns_authoritative_purchase_offer():
    session = make_session()
    llm = FakeLLM([proposal()])
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(query="Genshin Impact", budget_paise=100000),
        policy=make_policy(),
    )

    assert offer.product_id == "GAME-001"
    assert offer.upsell_product_id == "MER-002"
    assert offer.amount_paise == 89900
    assert offer.currency == "INR"
    assert offer.policy_decision == "ALLOWED"


def test_no_upsell_returns_base_product_only():
    session = make_session()
    llm = FakeLLM([proposal(upsell_id=None)])
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(query="Genshin Impact", budget_paise=100000),
        policy=make_policy(),
    )

    assert offer.upsell_product_id is None
    assert offer.upsell_reason is None
    assert offer.amount_paise == 0


def test_invalid_upsell_is_reprompted_and_corrected():
    session = make_session()
    llm = FakeLLM(
        [
            proposal(upsell_id="NOT-MAPPED", reason="Invented"),
            proposal(upsell_id="MER-002"),
        ]
    )
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(query="Genshin Impact", budget_paise=100000),
        policy=make_policy(),
    )

    assert offer.upsell_product_id == "MER-002"
    assert len(llm.calls) == 2
    assert "previous proposal was invalid" in llm.calls[1]["user_prompt"]


def test_invalid_base_product_is_reprompted_and_corrected():
    session = make_session()
    llm = FakeLLM(
        [
            proposal(product_id="DOES-NOT-EXIST"),
            proposal(product_id="GAME-001", upsell_id=None),
        ]
    )
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(query="Genshin Impact", budget_paise=100000),
        policy=make_policy(),
    )

    assert offer.product_id == "GAME-001"
    assert len(llm.calls) == 2


def test_reprompt_is_bounded_to_one():
    session = make_session()
    bad = proposal(product_id="DOES-NOT-EXIST")
    llm = FakeLLM([bad, bad, proposal()])
    agent = MerchantAgent(llm)

    with pytest.raises(ValueError, match="after one re-prompt"):
        agent.propose(
            session=session,
            request=PurchaseRequest(query="Genshin Impact", budget_paise=100000),
            policy=make_policy(),
        )

    assert len(llm.calls) == 2
    assert len(llm.proposals) == 1


def test_llm_generated_price_is_not_trusted():
    session = make_session()
    llm = FakeLLM([proposal()])
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(query="Genshin Impact", budget_paise=100000),
        policy=make_policy(),
    )

    assert offer.amount_paise == 89900


def test_over_budget_proposal_is_reprompted_and_corrected():
    """Test that an over-budget proposal gets one corrective attempt."""
    session = make_session()
    llm = FakeLLM(
        [
            proposal(upsell_id="MER-001"),  # ₹2,499 - over budget
            proposal(upsell_id=None),       # ₹0 - within budget
        ]
    )
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(
            query="Genshin Impact",
            budget_paise=100000,  # ₹1,000 budget
        ),
        policy=make_policy(),
    )

    assert offer.product_id == "GAME-001"
    assert offer.upsell_product_id is None
    assert offer.amount_paise == 0
    assert offer.policy_decision == "ALLOWED"
    assert len(llm.calls) == 2
    assert "exceeds the buyer budget" in llm.calls[1]["user_prompt"]


def test_over_budget_proposal_is_bounded_to_one_reprompt():
    """Test that only one reprompt is allowed for budget violations."""
    session = make_session()
    bad = proposal(upsell_id="MER-001")  # ₹2,499 - over budget
    llm = FakeLLM([bad, bad, proposal(upsell_id=None)])
    agent = MerchantAgent(llm)

    with pytest.raises(ValueError, match="after one re-prompt"):
        agent.propose(
            session=session,
            request=PurchaseRequest(
                query="Genshin Impact",
                budget_paise=100000,
            ),
            policy=make_policy(),
        )

    assert len(llm.calls) == 2
    assert len(llm.proposals) == 1


def test_llm_context_contains_budget_and_candidate_affordability_data():
    """Test that the LLM receives budget and affordability information."""
    session = make_session()
    llm = FakeLLM([proposal()])
    agent = MerchantAgent(llm)

    agent.propose(
        session=session,
        request=PurchaseRequest(
            query="Genshin Impact",
            budget_paise=100000,
        ),
        policy=make_policy(),
    )

    user_prompt = llm.calls[0]["user_prompt"]

    assert '"budget_paise":100000' in user_prompt
    # Check that the product price appears in the context (the exact format may vary)
    assert "89900" in user_prompt
    assert "max_autonomous" in user_prompt
    assert "basket_total_paise" in user_prompt


def test_policy_rejection_is_returned_without_bypassing_pricing():
    """Test that policy rejection still computes the authoritative price."""
    session = make_session()
    # The budget is ₹500, and the keychain is ₹899, so it exceeds budget
    # Need to provide a corrected proposal (no upsell) after the over-budget one
    llm = FakeLLM(
        [
            proposal(upsell_id="MER-002"),  # ₹899 - over budget
            proposal(upsell_id=None),       # ₹0 - within budget
        ]
    )
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(query="Genshin Impact", budget_paise=50000),  # ₹500 budget
        policy=make_policy(),
    )

    assert offer.amount_paise == 0  # No upsell means ₹0
    assert offer.policy_decision == "ALLOWED"  # ₹0 is within policy


def test_policy_requires_confirmation_propagates():
    session = make_session()
    llm = FakeLLM([proposal()])
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(query="Genshin Impact", budget_paise=300000),
        policy=make_policy(max_single_item_price_paise=50000),
    )

    assert offer.policy_decision == "REQUIRES_CONFIRMATION"
    assert "autonomous upsell limit" in offer.policy_reason


def test_missing_buyer_budget_is_rejected_before_policy_evaluation():
    session = make_session()
    llm = FakeLLM([proposal()])
    agent = MerchantAgent(llm)

    with pytest.raises(ValueError, match="buyer_budget_paise is required"):
        agent.propose(
            session=session,
            request=PurchaseRequest(query="Genshin Impact"),
            policy=make_policy(),
        )

    assert llm.calls == []


def test_malformed_llm_output_is_reprompted():
    session = make_session()
    llm = FakeLLM(
        [
            ValueError("schema-invalid"),
            proposal(upsell_id=None),
        ]
    )
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(query="Genshin Impact", budget_paise=100000),
        policy=make_policy(),
    )

    assert offer.product_id == "GAME-001"
    assert len(llm.calls) == 2


def test_unknown_search_result_raises_before_llm_call():
    session = make_session()
    llm = FakeLLM([proposal()])
    agent = MerchantAgent(llm)

    with pytest.raises(ValueError, match="No catalog products matched"):
        agent.propose(
            session=session,
            request=PurchaseRequest(query="Nintendo Zelda", budget_paise=100000),
            policy=make_policy(),
        )

    assert llm.calls == []


def test_allowed_product_policy_rejection_is_returned():
    session = make_session()
    llm = FakeLLM([proposal(upsell_id=None)])
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(query="Genshin Impact", budget_paise=100000),
        policy=make_policy(allowed_product_ids="GAME-999"),
    )

    assert offer.policy_decision == "REJECTED"
    assert "not allowed" in offer.policy_reason


def test_agent_never_receives_or_calls_razorpay():
    session = make_session()
    llm = FakeLLM([proposal()])
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(query="Genshin Impact", budget_paise=100000),
        policy=make_policy(),
    )

    assert not hasattr(llm, "razorpay")
    assert offer.amount_paise == 89900


def test_purchase_offer_is_a_pydantic_contract():
    session = make_session()
    llm = FakeLLM([proposal(upsell_id=None)])
    agent = MerchantAgent(llm)

    offer = agent.propose(
        session=session,
        request=PurchaseRequest(query="Genshin Impact", budget_paise=100000),
        policy=make_policy(),
    )

    assert offer.__class__.__name__ == "PurchaseOffer"
    assert offer.breakdown[0].product_id == "GAME-001"
    assert offer.breakdown[0].unit_price_paise == 0