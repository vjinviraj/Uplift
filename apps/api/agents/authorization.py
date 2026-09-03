from apps.api.agents.schemas import PurchaseConfirmation, PurchaseOffer


def authorize_purchase(
    *,
    offer: PurchaseOffer,
    confirmation: PurchaseConfirmation,
) -> bool:
    """Return True only when merchant policy and buyer approval both pass."""

    if offer.policy_decision == "REJECTED":
        return False

    if not confirmation.approved:
        return False

    if confirmation.amount_paise != offer.amount_paise:
        return False

    if offer.policy_decision == "REQUIRES_CONFIRMATION":
        return True

    if offer.policy_decision == "ALLOWED":
        return True

    return False