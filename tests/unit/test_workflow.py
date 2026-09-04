from unittest.mock import Mock

import pytest

from apps.api.agents.buyer import AIBuyer
from apps.api.agents.merchant_agent import MerchantAgent
from apps.api.agents.schemas import (
    PurchaseConfirmation,
    PurchaseOffer,
    PurchaseRequest,
)
from apps.api.agents.workflow import PurchaseWorkflow
from apps.api.agents.authorization import hash_offer
from apps.api.models import PolicyConfig, PurchaseApproval


def make_policy() -> PolicyConfig:
    return PolicyConfig(
        version="v1",
        max_single_item_price_paise=100_000,
        max_order_total_without_extra_confirm_paise=500_000,
        max_upsells_per_session=1,
        allowed_product_ids=None,
    )


def make_offer(
    *,
    amount_paise: int = 89_900,
    policy_decision: str = "ALLOWED",
) -> PurchaseOffer:
    return PurchaseOffer(
        product_id="GAME-001",
        upsell_product_id=None,
        upsell_reason=None,
        amount_paise=amount_paise,
        currency="INR",
        breakdown=[
            {
                "product_id": "GAME-001",
                "name": "Genshin Impact - Digital Edition",
                "qty": 1,
                "unit_price_paise": amount_paise,
                "line_total_paise": amount_paise,
            }
        ],
        policy_decision=policy_decision,
        policy_reason="Test policy result.",
        policy_version="v1",
    )


def make_session_with_approval(
    *,
    session_id: str,
    offer: PurchaseOffer,
    confirmation: PurchaseConfirmation,
    amount_paise: int | None = None,
    policy_version: str | None = None,
    offer_hash: str | None = None,
    approved: bool = True,
    extra_confirmation: bool | None = None,
) -> Mock:
    session = Mock()
    exec_result = Mock()
    exec_result.first.return_value = PurchaseApproval(
        id=1,
        session_id=session_id,
        approved=approved,
        amount_paise=offer.amount_paise if amount_paise is None else amount_paise,
        policy_version=offer.policy_version if policy_version is None else policy_version,
        offer_hash=hash_offer(offer) if offer_hash is None else offer_hash,
        extra_confirmation=(
            confirmation.extra_confirmation
            if extra_confirmation is None
            else extra_confirmation
        ),
    )
    session.exec.return_value = exec_result
    return session


def test_authorized_order_calls_create_order(monkeypatch):
    workflow = PurchaseWorkflow(
        merchant_agent=Mock(spec=MerchantAgent),
        buyer=Mock(spec=AIBuyer),
    )
    offer = make_offer()
    confirmation = PurchaseConfirmation(approved=True, amount_paise=89_900)
    session = make_session_with_approval(
        session_id="session-001",
        offer=offer,
        confirmation=confirmation,
    )

    monkeypatch.setattr(
        "apps.api.agents.workflow.authorize_purchase",
        lambda *, offer, confirmation: True,
    )
    create_order = Mock(return_value="created-order")
    monkeypatch.setattr("apps.api.agents.workflow.create_order", create_order)

    result = workflow.create_authorized_order(
        session=session,
        razorpay_client=Mock(),
        session_id="session-001",
        offer=offer,
        confirmation=confirmation,
        idempotency_key="idem-001",
    )

    assert result == "created-order"
    create_order.assert_called_once_with(
        session=create_order.call_args.kwargs["session"],
        razorpay_client=create_order.call_args.kwargs["razorpay_client"],
        session_id="session-001",
        amount_paise=89_900,
        idempotency_key="idem-001",
    )


def test_unauthorized_purchase_does_not_call_create_order(monkeypatch):
    workflow = PurchaseWorkflow(
        merchant_agent=Mock(spec=MerchantAgent),
        buyer=Mock(spec=AIBuyer),
    )
    monkeypatch.setattr(
        "apps.api.agents.workflow.authorize_purchase",
        lambda *, offer, confirmation: False,
    )
    create_order = Mock()
    monkeypatch.setattr("apps.api.agents.workflow.create_order", create_order)

    with pytest.raises(ValueError, match="not authorized"):
        workflow.create_authorized_order(
            session=Mock(),
            razorpay_client=Mock(),
            session_id="session-002",
            offer=make_offer(),
            confirmation=PurchaseConfirmation(
                approved=False,
                amount_paise=89_900,
            ),
            idempotency_key="idem-002",
        )

    create_order.assert_not_called()


def test_execute_passes_offer_to_buyer_and_authorization(monkeypatch):
    merchant_agent = Mock(spec=MerchantAgent)
    buyer = Mock(spec=AIBuyer)
    workflow = PurchaseWorkflow(merchant_agent=merchant_agent, buyer=buyer)
    request = PurchaseRequest(query="Genshin Impact", budget_paise=100_000)
    offer = make_offer()
    confirmation = PurchaseConfirmation(approved=True, amount_paise=89_900)
    merchant_agent.propose.return_value = offer
    buyer.evaluate_offer.return_value = confirmation
    monkeypatch.setattr(
        "apps.api.agents.workflow.authorize_purchase",
        lambda *, offer, confirmation: True,
    )
    create_order = Mock(return_value="order")
    monkeypatch.setattr("apps.api.agents.workflow.create_order", create_order)
    session = make_session_with_approval(
        session_id="session-003",
        offer=offer,
        confirmation=confirmation,
    )

    returned_offer, returned_confirmation = workflow.execute(
        session=session,
        request=request,
        policy=make_policy(),
        razorpay_client=Mock(),
        session_id="session-003",
        idempotency_key="idem-003",
    )

    assert returned_offer is offer
    assert returned_confirmation is confirmation
    merchant_agent.propose.assert_called_once()
    buyer.evaluate_offer.assert_called_once_with(request=request, offer=offer)
    create_order.assert_called_once()


def test_execute_does_not_create_order_when_buyer_rejects(monkeypatch):
    merchant_agent = Mock(spec=MerchantAgent)
    buyer = Mock(spec=AIBuyer)
    workflow = PurchaseWorkflow(merchant_agent=merchant_agent, buyer=buyer)
    request = PurchaseRequest(query="Genshin Impact", budget_paise=50_000)
    offer = make_offer()
    confirmation = PurchaseConfirmation(approved=False, amount_paise=89_900)
    merchant_agent.propose.return_value = offer
    buyer.evaluate_offer.return_value = confirmation
    monkeypatch.setattr(
        "apps.api.agents.workflow.authorize_purchase",
        lambda *, offer, confirmation: False,
    )
    create_order = Mock()
    monkeypatch.setattr("apps.api.agents.workflow.create_order", create_order)

    with pytest.raises(ValueError, match="not authorized"):
        workflow.execute(
            session=Mock(),
            request=request,
            policy=make_policy(),
            razorpay_client=Mock(),
            session_id="session-004",
            idempotency_key="idem-004",
        )

    create_order.assert_not_called()


def test_execute_never_uses_a_buyer_supplied_amount_for_payment(monkeypatch):
    merchant_agent = Mock(spec=MerchantAgent)
    buyer = Mock(spec=AIBuyer)
    workflow = PurchaseWorkflow(merchant_agent=merchant_agent, buyer=buyer)
    request = PurchaseRequest(query="Genshin Impact", budget_paise=100_000)
    offer = make_offer(amount_paise=89_900)
    confirmation = PurchaseConfirmation(approved=True, amount_paise=89_900)
    merchant_agent.propose.return_value = offer
    buyer.evaluate_offer.return_value = confirmation
    monkeypatch.setattr(
        "apps.api.agents.workflow.authorize_purchase",
        lambda *, offer, confirmation: True,
    )
    create_order = Mock(return_value="order")
    monkeypatch.setattr("apps.api.agents.workflow.create_order", create_order)
    session = make_session_with_approval(
        session_id="session-005",
        offer=offer,
        confirmation=confirmation,
    )

    workflow.execute(
        session=session,
        request=request,
        policy=make_policy(),
        razorpay_client=Mock(),
        session_id="session-005",
        idempotency_key="idem-005",
    )

    assert create_order.call_args.kwargs["amount_paise"] == 89_900


def test_durable_approval_hash_mismatch_blocks_payment(monkeypatch):
    workflow = PurchaseWorkflow(
        merchant_agent=Mock(spec=MerchantAgent),
        buyer=Mock(spec=AIBuyer),
    )
    offer = make_offer()
    confirmation = PurchaseConfirmation(approved=True, amount_paise=89_900)
    session = make_session_with_approval(
        session_id="session-006",
        offer=offer,
        confirmation=confirmation,
        offer_hash="tampered-hash",
    )
    monkeypatch.setattr(
        "apps.api.agents.workflow.authorize_purchase",
        lambda *, offer, confirmation: True,
    )
    create_order = Mock()
    monkeypatch.setattr("apps.api.agents.workflow.create_order", create_order)

    with pytest.raises(ValueError, match="offer does not match"):
        workflow.create_authorized_order(
            session=session,
            razorpay_client=Mock(),
            session_id="session-006",
            offer=offer,
            confirmation=confirmation,
            idempotency_key="idem-006",
        )

    create_order.assert_not_called()


def test_requires_confirmation_needs_durable_extra_confirmation(monkeypatch):
    workflow = PurchaseWorkflow(
        merchant_agent=Mock(spec=MerchantAgent),
        buyer=Mock(spec=AIBuyer),
    )
    offer = make_offer(
        amount_paise=150_000,
        policy_decision="REQUIRES_CONFIRMATION",
    )
    confirmation = PurchaseConfirmation(
        approved=True,
        amount_paise=150_000,
        extra_confirmation=True,
    )
    session = make_session_with_approval(
        session_id="session-007",
        offer=offer,
        confirmation=confirmation,
        extra_confirmation=False,
    )
    monkeypatch.setattr(
        "apps.api.agents.workflow.authorize_purchase",
        lambda *, offer, confirmation: True,
    )
    create_order = Mock()
    monkeypatch.setattr("apps.api.agents.workflow.create_order", create_order)

    with pytest.raises(ValueError, match="confirmation does not match"):
        workflow.create_authorized_order(
            session=session,
            razorpay_client=Mock(),
            session_id="session-007",
            offer=offer,
            confirmation=confirmation,
            idempotency_key="idem-007",
        )

    create_order.assert_not_called()
