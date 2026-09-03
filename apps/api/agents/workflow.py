from sqlmodel import Session

from apps.api.agents.authorization import authorize_purchase
from apps.api.agents.buyer import AIBuyer
from apps.api.agents.merchant_agent import MerchantAgent
from apps.api.agents.schemas import PurchaseConfirmation, PurchaseOffer, PurchaseRequest
from apps.api.models import PolicyConfig
from apps.api.razorpay_client.service import create_order


class PurchaseWorkflow:
    """Coordinate the AI Buyer, Merchant Agent, authorization, and payment boundary."""

    def __init__(
        self,
        *,
        merchant_agent: MerchantAgent,
        buyer: AIBuyer,
    ) -> None:
        self.merchant_agent = merchant_agent
        self.buyer = buyer

    def prepare_offer(
        self,
        *,
        session: Session,
        request: PurchaseRequest,
        policy: PolicyConfig,
    ) -> PurchaseOffer:
        return self.merchant_agent.propose(
            session=session,
            request=request,
            policy=policy,
        )

    def evaluate_offer(
        self,
        *,
        request: PurchaseRequest,
        offer: PurchaseOffer,
    ) -> PurchaseConfirmation:
        return self.buyer.evaluate_offer(
            request=request,
            offer=offer,
        )

    def authorize(
        self,
        *,
        offer: PurchaseOffer,
        confirmation: PurchaseConfirmation,
    ) -> bool:
        return authorize_purchase(
            offer=offer,
            confirmation=confirmation,
        )

    def create_authorized_order(
        self,
        *,
        session: Session,
        razorpay_client,
        session_id: str,
        offer: PurchaseOffer,
        confirmation: PurchaseConfirmation,
        idempotency_key: str,
    ):
        if not self.authorize(
            offer=offer,
            confirmation=confirmation,
        ):
            raise ValueError("Purchase is not authorized")

        return create_order(
            session=session,
            razorpay_client=razorpay_client,
            session_id=session_id,
            amount_paise=offer.amount_paise,
            idempotency_key=idempotency_key,
        )

    def execute(
        self,
        *,
        session: Session,
        request: PurchaseRequest,
        policy: PolicyConfig,
        razorpay_client,
        session_id: str,
        idempotency_key: str,
    ) -> tuple[PurchaseOffer, PurchaseConfirmation]:
        offer = self.prepare_offer(
            session=session,
            request=request,
            policy=policy,
        )

        confirmation = self.evaluate_offer(
            request=request,
            offer=offer,
        )

        self.create_authorized_order(
            session=session,
            razorpay_client=razorpay_client,
            session_id=session_id,
            offer=offer,
            confirmation=confirmation,
            idempotency_key=idempotency_key,
        )

        return offer, confirmation
