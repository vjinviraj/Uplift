from apps.api.agents.schemas import PurchaseOffer, PurchaseRequest
from apps.api.agents.buyer import AIBuyer


def make_offer(
    *,
    amount_paise: int = 89900,
    policy_decision: str = "ALLOWED",
) -> PurchaseOffer:
    return PurchaseOffer(
        product_id="GAME-001",
        upsell_product_id="MER-002",
        upsell_reason="Relevant merchandise.",
        amount_paise=amount_paise,
        currency="INR",
        breakdown=[
            {
                "product_id": "GAME-001",
                "name": "Genshin Impact - Digital Edition",
                "qty": 1,
                "unit_price_paise": 0,
                "line_total_paise": 0,
            },
            {
                "product_id": "MER-002",
                "name": "Genshin Impact Vision Keychain - Pyro Edition",
                "qty": 1,
                "unit_price_paise": 89900,
                "line_total_paise": 89900,
            },
        ],
        policy_decision=policy_decision,
        policy_reason="Test policy result.",
        policy_version="v1",
    )


def test_buyer_approves_offer_within_budget():
    buyer = AIBuyer()
    request = PurchaseRequest(query="Genshin Impact", budget_paise=100000)

    confirmation = buyer.evaluate_offer(
        request=request,
        offer=make_offer(amount_paise=89900),
    )

    assert confirmation.approved is True
    assert confirmation.amount_paise == 89900


def test_buyer_rejects_offer_above_budget():
    buyer = AIBuyer()
    request = PurchaseRequest(query="Genshin Impact", budget_paise=50000)

    confirmation = buyer.evaluate_offer(
        request=request,
        offer=make_offer(amount_paise=89900),
    )

    assert confirmation.approved is False
    assert confirmation.amount_paise == 89900


def test_buyer_rejects_policy_rejected_offer():
    buyer = AIBuyer()
    request = PurchaseRequest(query="Genshin Impact", budget_paise=100000)

    confirmation = buyer.evaluate_offer(
        request=request,
        offer=make_offer(policy_decision="REJECTED"),
    )

    assert confirmation.approved is False
    assert confirmation.amount_paise == 89900


def test_buyer_can_approve_requires_confirmation_offer_when_within_budget():
    buyer = AIBuyer()
    request = PurchaseRequest(query="Genshin Impact", budget_paise=200000)

    confirmation = buyer.evaluate_offer(
        request=request,
        offer=make_offer(policy_decision="REQUIRES_CONFIRMATION"),
    )

    assert confirmation.approved is True
    assert confirmation.amount_paise == 89900


def test_buyer_requires_budget():
    buyer = AIBuyer()
    request = PurchaseRequest(query="Genshin Impact")

    try:
        buyer.evaluate_offer(
            request=request,
            offer=make_offer(),
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "buyer_budget_paise" in str(exc)


def test_buyer_confirmation_uses_exact_server_offer_amount():
    buyer = AIBuyer()
    request = PurchaseRequest(query="Genshin Impact", budget_paise=100000)
    offer = make_offer(amount_paise=89900)

    confirmation = buyer.evaluate_offer(request=request, offer=offer)

    assert confirmation.amount_paise == offer.amount_paise