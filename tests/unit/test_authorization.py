from apps.api.agents.authorization import authorize_purchase
from apps.api.agents.schemas import PurchaseConfirmation, PurchaseOffer


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


def test_authorizes_allowed_offer_with_exact_buyer_approval():
    offer = make_offer()
    confirmation = PurchaseConfirmation(
        approved=True,
        amount_paise=89900,
    )
    assert authorize_purchase(
        offer=offer,
        confirmation=confirmation,
    ) is True


def test_rejects_when_buyer_does_not_approve():
    offer = make_offer()
    confirmation = PurchaseConfirmation(
        approved=False,
        amount_paise=89900,
    )
    assert authorize_purchase(
        offer=offer,
        confirmation=confirmation,
    ) is False


def test_rejects_when_buyer_approves_wrong_amount():
    offer = make_offer(amount_paise=89900)
    confirmation = PurchaseConfirmation(
        approved=True,
        amount_paise=79900,
    )
    assert authorize_purchase(
        offer=offer,
        confirmation=confirmation,
    ) is False


def test_rejects_policy_rejected_offer():
    offer = make_offer(policy_decision="REJECTED")
    confirmation = PurchaseConfirmation(
        approved=True,
        amount_paise=89900,
    )
    assert authorize_purchase(
        offer=offer,
        confirmation=confirmation,
    ) is False


def test_requires_extra_confirmation_for_requires_confirmation_offer():
    offer = make_offer(
        amount_paise=150000,
        policy_decision="REQUIRES_CONFIRMATION",
    )

    without_extra_confirmation = PurchaseConfirmation(
        approved=True,
        amount_paise=150000,
        extra_confirmation=False,
    )
    assert authorize_purchase(
        offer=offer,
        confirmation=without_extra_confirmation,
    ) is False

    with_extra_confirmation = PurchaseConfirmation(
        approved=True,
        amount_paise=150000,
        extra_confirmation=True,
    )
    assert authorize_purchase(
        offer=offer,
        confirmation=with_extra_confirmation,
    ) is True


def test_requires_exact_amount_even_when_policy_allows():
    offer = make_offer(amount_paise=89900)
    confirmation = PurchaseConfirmation(
        approved=True,
        amount_paise=90000,
    )
    assert authorize_purchase(
        offer=offer,
        confirmation=confirmation,
    ) is False


def test_unknown_policy_decision_is_rejected():
    offer = make_offer(policy_decision="SOMETHING_ELSE")
    confirmation = PurchaseConfirmation(
        approved=True,
        amount_paise=89900,
    )
    assert authorize_purchase(
        offer=offer,
        confirmation=confirmation,
    ) is False
