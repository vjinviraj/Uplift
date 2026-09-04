import hashlib

from apps.api.agents.schemas import PurchaseConfirmation, PurchaseOffer


def hash_offer(offer: PurchaseOffer) -> str:
    return hashlib.sha256(
        offer.model_dump_json().encode("utf-8")
    ).hexdigest()


def authorize_purchase(
    *,
    offer: PurchaseOffer,
    confirmation: PurchaseConfirmation,
) -> bool:
    if offer.policy_decision == "REJECTED":
        return False

    if not confirmation.approved:
        return False

    if confirmation.amount_paise != offer.amount_paise:
        return False

    if offer.policy_decision == "REQUIRES_CONFIRMATION":
        return confirmation.extra_confirmation

    if offer.policy_decision == "ALLOWED":
        return True

    return False
