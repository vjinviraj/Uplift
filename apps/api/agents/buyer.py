from apps.api.agents.schemas import PurchaseConfirmation, PurchaseOffer, PurchaseRequest


class AIBuyer:
    """Lightweight buyer-side evaluation before payment authorization.

    The buyer can approve an offer only when the server-computed amount is
    within the buyer's stated budget and the merchant policy has not rejected
    the offer. The buyer never calls Razorpay.
    """

    def evaluate_offer(
        self,
        *,
        request: PurchaseRequest,
        offer: PurchaseOffer,
    ) -> PurchaseConfirmation:
        if request.budget_paise is None:
            raise ValueError("buyer_budget_paise is required for offer evaluation")

        if offer.amount_paise > request.budget_paise:
            return PurchaseConfirmation(
                approved=False,
                amount_paise=offer.amount_paise,
            )

        if offer.policy_decision == "REJECTED":
            return PurchaseConfirmation(
                approved=False,
                amount_paise=offer.amount_paise,
            )

        return PurchaseConfirmation(
            approved=True,
            amount_paise=offer.amount_paise,
        )