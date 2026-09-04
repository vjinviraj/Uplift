import json
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

from apps.api.agents.authorization import hash_offer
from apps.api.agents.buyer import AIBuyer
from apps.api.agents.llm_client import LLMClient
from apps.api.agents.merchant_agent import MerchantAgent
from apps.api.agents.schemas import PurchaseConfirmation, PurchaseOffer, PurchaseRequest
from apps.api.agents.workflow import PurchaseWorkflow
from apps.api.config import get_setting
from apps.api.database import create_db_and_tables, get_session
from apps.api.models import (
    AuditEvent,
    Order,
    Payment,
    PolicyConfig,
    PurchaseApproval,
    PurchaseSessionState,
    ExperimentObservation,
)
from apps.api.razorpay_client.client import get_razorpay_client
from apps.api.razorpay_client.reconciliation import reconcile_payment
from apps.api.razorpay_client.service import (
    create_order,
    record_payment_failure,
    retry_order,
)
from apps.api.razorpay_client.verification import verify_payment_signature


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Uplift API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "null"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class PaymentVerificationRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


class PaymentFailureRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str


class PurchaseApprovalRequest(BaseModel):
    approved: bool
    amount_paise: int
    extra_confirmation: bool = False


class PurchasePreparationResponse(BaseModel):
    session_id: str
    status: str
    request: PurchaseRequest
    offer: PurchaseOffer


class PurchaseApprovalResponse(BaseModel):
    session_id: str
    status: str
    approved: bool
    amount_paise: int
    currency: str
    order_id: str | None = None
    key_id: str | None = None
    local_order_id: int | None = None


class PurchasePaymentVerificationResponse(BaseModel):
    session_id: str
    status: str
    razorpay_order_id: str
    razorpay_payment_id: str | None = None
    message: str | None = None


# ===== Purchase Retry Response Model =====

class PurchaseRetryResponse(BaseModel):
    session_id: str
    status: str
    retry_count: int
    amount_paise: int
    currency: str
    order_id: str
    local_order_id: int
    key_id: str


# ===== Overview Response Models =====

class OverviewTransaction(BaseModel):
    session_id: str
    local_order_id: int
    razorpay_order_id: str | None = None
    product_name: str
    amount_paise: int
    currency: str
    status: str

class OverviewResponse(BaseModel):
    sessions: int
    revenue_paise: int
    aov_paise: int
    upsell_acceptance_pct: float
    upsell_orders: int
    paid_orders: int
    recent_transactions: list[OverviewTransaction]


# ===== Transaction Response Models =====

class TransactionPayment(BaseModel):
    id: int
    razorpay_payment_id: str
    status: str
    method: str
    verified_at: str | None = None
    failure_reason: str | None = None


class TransactionAuditEvent(BaseModel):
    id: int
    timestamp: str
    actor_type: str
    action_id: str
    event_type: str
    decision: str | None = None
    reason: str | None = None
    policy_version: str | None = None
    buyer_budget_paise: int | None = None
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    payload: dict


class TransactionResponse(BaseModel):
    session_id: str
    status: str

    request: PurchaseRequest
    offer: PurchaseOffer

    order_id: int | None = None
    amount_paise: int
    currency: str
    order_status: str | None = None
    razorpay_order_id: str | None = None

    buyer_approval_amount_paise: int | None = None
    buyer_approval_recorded: bool

    authorization_status: str

    payments: list[TransactionPayment]
    audit_events: list[TransactionAuditEvent]


class ExperimentArmMetrics(BaseModel):
    sessions: int
    successful_orders: int
    revenue_paise: int
    aov_paise: int
    conversion_pct: float


class ExperimentSummaryResponse(BaseModel):
    methodology: str
    treatment: ExperimentArmMetrics
    control: ExperimentArmMetrics
    aov_lift_pct: float | None
    revenue_delta_per_session_paise: float | None
    upsell_acceptance_pct: float
    blocked_unsafe_actions: int
    payment_recovery_pct: float | None


class AuditLogEvent(BaseModel):
    id: int
    timestamp: str
    session_id: str
    actor_type: str
    action_id: str
    event_type: str
    decision: str | None = None
    reason: str | None = None
    policy_version: str | None = None
    buyer_budget_paise: int | None = None
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    payload: dict


class AuditLogResponse(BaseModel):
    events: list[AuditLogEvent]


def load_policy(session: Session) -> PolicyConfig:
    policy = session.exec(select(PolicyConfig)).first()
    if policy is not None:
        return policy

    return PolicyConfig(
        version="api-v1",
        max_single_item_price_paise=100_000,
        max_order_total_without_extra_confirm_paise=500_000,
        max_upsells_per_session=1,
        allowed_product_ids=None,
    )


def build_workflow() -> PurchaseWorkflow:
    llm_client = LLMClient()
    return PurchaseWorkflow(
        merchant_agent=MerchantAgent(llm_client),
        buyer=AIBuyer(),
    )



@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/overview", response_model=OverviewResponse)
def get_overview(
    session: Session = Depends(get_session),
):
    purchase_sessions = session.exec(
        select(PurchaseSessionState)
    ).all()

    orders = session.exec(
        select(Order)
    ).all()

    paid_orders = [
        order
        for order in orders
        if order.status == "PAID"
    ]

    revenue_paise = sum(
        order.amount_paise
        for order in paid_orders
    )

    aov_paise = (
        round(revenue_paise / len(paid_orders))
        if paid_orders
        else 0
    )

    upsell_proposed_sessions = 0
    upsell_accepted_sessions = 0

    orders_by_session = {
        order.session_id: order
        for order in orders
    }

    for purchase_session in purchase_sessions:
        try:
            offer = PurchaseOffer.model_validate_json(
                purchase_session.offer_json
            )
        except ValueError:
            continue

        if offer.upsell_product_id is None:
            continue

        upsell_proposed_sessions += 1

        if purchase_session.id in orders_by_session:
            upsell_accepted_sessions += 1

    upsell_acceptance_pct = (
        round(
            upsell_accepted_sessions
            / upsell_proposed_sessions
            * 100,
            1,
        )
        if upsell_proposed_sessions
        else 0.0
    )

    recent_orders = sorted(
        orders,
        key=lambda order: order.id,
        reverse=True,
    )[:10]

    recent_transactions: list[OverviewTransaction] = []

    for order in recent_orders:
        product_name = "Purchase"

        if order.session_id:
            purchase_session = session.get(
                PurchaseSessionState,
                order.session_id,
            )

            if purchase_session is not None:
                try:
                    offer = PurchaseOffer.model_validate_json(
                        purchase_session.offer_json
                    )

                    product_name = offer.product_id

                    for item in offer.breakdown:
                        if item.product_id == offer.product_id:
                            product_name = item.name
                            break
                except ValueError:
                    pass

        recent_transactions.append(
            OverviewTransaction(
                session_id=order.session_id,
                local_order_id=order.id,
                razorpay_order_id=order.razorpay_order_id,
                product_name=product_name,
                amount_paise=order.amount_paise,
                currency=order.currency,
                status=order.status,
            )
        )

    return OverviewResponse(
        sessions=len(purchase_sessions),
        revenue_paise=revenue_paise,
        aov_paise=aov_paise,
        upsell_acceptance_pct=upsell_acceptance_pct,
        upsell_orders=upsell_accepted_sessions,
        paid_orders=len(paid_orders),
        recent_transactions=recent_transactions,
    )


@app.post("/api/purchases/prepare", response_model=PurchasePreparationResponse)
def prepare_purchase(
    request: PurchaseRequest,
    session: Session = Depends(get_session),
):
    try:
        workflow = build_workflow()
        offer = workflow.prepare_offer(
            session=session,
            request=request,
            policy=load_policy(session),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_id = f"purchase-{uuid4().hex}"
    snapshot = PurchaseSessionState(
        id=session_id,
        request_json=request.model_dump_json(),
        offer_json=offer.model_dump_json(),
        status="AWAITING_APPROVAL",
    )
    session.add(snapshot)
    session.commit()

    return PurchasePreparationResponse(
        session_id=session_id,
        status=snapshot.status,
        request=request,
        offer=offer,
    )


@app.get("/api/purchases/{session_id}", response_model=PurchasePreparationResponse)
def get_purchase(
    session_id: str,
    session: Session = Depends(get_session),
):
    snapshot = session.get(PurchaseSessionState, session_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Purchase session not found")

    return PurchasePreparationResponse(
        session_id=snapshot.id,
        status=snapshot.status,
        request=PurchaseRequest.model_validate_json(snapshot.request_json),
        offer=PurchaseOffer.model_validate_json(snapshot.offer_json),
    )


@app.get(
    "/api/transactions/{session_id}",
    response_model=TransactionResponse,
)
def get_transaction(
    session_id: str,
    session: Session = Depends(get_session),
):
    snapshot = session.get(PurchaseSessionState, session_id)

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    request = PurchaseRequest.model_validate_json(
        snapshot.request_json
    )
    offer = PurchaseOffer.model_validate_json(
        snapshot.offer_json
    )

    approval_record = session.exec(
        select(PurchaseApproval)
        .where(PurchaseApproval.session_id == session_id)
        .order_by(PurchaseApproval.id.desc())
    ).first()

    order = session.exec(
        select(Order)
        .where(Order.session_id == session_id)
        .order_by(Order.id.desc())
    ).first()

    payments: list[TransactionPayment] = []

    if order is not None:
        payment_records = session.exec(
            select(Payment)
            .where(Payment.order_id == order.id)
            .order_by(Payment.id.desc())
        ).all()

        payments = [
            TransactionPayment(
                id=payment.id,
                razorpay_payment_id=payment.razorpay_payment_id,
                status=payment.status,
                method=payment.method,
                verified_at=(
                    payment.verified_at.isoformat()
                    if payment.verified_at is not None
                    else None
                ),
                failure_reason=payment.failure_reason,
            )
            for payment in payment_records
        ]

    audit_records = session.exec(
        select(AuditEvent)
        .where(AuditEvent.session_id == session_id)
        .order_by(AuditEvent.timestamp.asc(), AuditEvent.id.asc())
    ).all()

    audit_events: list[TransactionAuditEvent] = []

    for event in audit_records:
        try:
            payload = json.loads(event.payload_json)
        except (TypeError, json.JSONDecodeError):
            payload = {
                "raw": event.payload_json,
            }

        audit_events.append(
            TransactionAuditEvent(
                id=event.id,
                timestamp=event.timestamp.isoformat(),
                actor_type=event.actor_type,
                action_id=event.action_id,
                event_type=event.event_type,
                decision=event.decision,
                reason=event.reason,
                policy_version=event.policy_version,
                buyer_budget_paise=event.buyer_budget_paise,
                razorpay_order_id=event.razorpay_order_id,
                razorpay_payment_id=event.razorpay_payment_id,
                payload=payload,
            )
        )

    return TransactionResponse(
        session_id=session_id,
        status=snapshot.status,
        request=request,
        offer=offer,
        order_id=order.id if order is not None else None,
        amount_paise=(
            order.amount_paise
            if order is not None
            else offer.amount_paise
        ),
        currency=(
            order.currency
            if order is not None
            else offer.currency
        ),
        order_status=order.status if order is not None else None,
        razorpay_order_id=(
            order.razorpay_order_id
            if order is not None
            else None
        ),
        buyer_approval_amount_paise=(
            approval_record.amount_paise
            if approval_record is not None and approval_record.approved
            else None
        ),
        buyer_approval_recorded=(
            approval_record is not None and approval_record.approved
        ),
        authorization_status=(
            "AUTHORIZED_ORDER_CREATED"
            if order is not None
            else (
                "BUYER_APPROVAL_RECORDED"
                if approval_record is not None and approval_record.approved
                else "NOT_AUTHORIZED"
            )
        ),
        payments=payments,
        audit_events=audit_events,
    )


@app.post("/api/purchases/{session_id}/approve", response_model=PurchaseApprovalResponse)
def approve_purchase(
    session_id: str,
    request: PurchaseApprovalRequest,
    session: Session = Depends(get_session),
):
    snapshot = session.get(PurchaseSessionState, session_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Purchase session not found")

    if snapshot.status != "AWAITING_APPROVAL":
        raise HTTPException(
            status_code=409,
            detail=f"Purchase session is already {snapshot.status}",
        )

    purchase_request = PurchaseRequest.model_validate_json(snapshot.request_json)
    offer = PurchaseOffer.model_validate_json(snapshot.offer_json)

    if request.amount_paise != offer.amount_paise:
        raise HTTPException(
            status_code=409,
            detail="Approved amount must exactly match the server-computed offer",
        )

    if not request.approved:
        snapshot.status = "REJECTED"
        session.add(snapshot)
        session.commit()
        return PurchaseApprovalResponse(
            session_id=session_id,
            status=snapshot.status,
            approved=False,
            amount_paise=offer.amount_paise,
            currency=offer.currency,
        )

    try:
        workflow = build_workflow()
        confirmation: PurchaseConfirmation = workflow.evaluate_offer(
            request=purchase_request,
            offer=offer,
        )

        # The explicit approval request supplies the additional confirmation
        # required for offers marked REQUIRES_CONFIRMATION.
        confirmation.extra_confirmation = request.extra_confirmation

        approval_record = PurchaseApproval(
            session_id=session_id,
            approved=confirmation.approved,
            amount_paise=confirmation.amount_paise,
            policy_version=offer.policy_version,
            offer_hash=hash_offer(offer),
            extra_confirmation=confirmation.extra_confirmation,
        )

        # Persist buyer approval evidence before entering the payment boundary.
        session.add(approval_record)
        session.commit()
        session.refresh(approval_record)

        session.add(
            AuditEvent(
                agent_run_id=str(uuid4()),
                session_id=session_id,
                actor_type="buyer",
                action_id="buyer-approval",
                event_type="buyer_approval_recorded",
                entity_type="PurchaseApproval",
                entity_id=str(approval_record.id),
                decision=(
                    "APPROVED"
                    if approval_record.approved
                    else "REJECTED"
                ),
                reason="Buyer approval recorded with exact offer binding",
                policy_version=approval_record.policy_version,
                buyer_budget_paise=purchase_request.budget_paise,
                payload_json=json.dumps(
                    {
                        "approved": approval_record.approved,
                        "amount_paise": approval_record.amount_paise,
                        "policy_version": approval_record.policy_version,
                        "offer_hash": approval_record.offer_hash,
                        "extra_confirmation": approval_record.extra_confirmation,
                        "confirmed_at": approval_record.confirmed_at.isoformat(),
                    }
                ),
            )
        )
        session.commit()

        order = workflow.create_authorized_order(
            session=session,
            razorpay_client=get_razorpay_client(),
            session_id=session_id,
            offer=offer,
            confirmation=confirmation,
            idempotency_key=f"uplift-{session_id}",
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    snapshot.status = "ORDER_CREATED"
    session.add(snapshot)
    session.commit()

    key_id = get_setting("RAZORPAY_KEY_ID")
    if not key_id:
        raise HTTPException(status_code=500, detail="RAZORPAY_KEY_ID must be configured")

    return PurchaseApprovalResponse(
        session_id=session_id,
        status=snapshot.status,
        approved=confirmation.approved,
        amount_paise=confirmation.amount_paise,
        currency=offer.currency,
        order_id=order.razorpay_order_id,
        key_id=key_id,
        local_order_id=order.id,
    )


@app.post(
    "/api/purchases/{session_id}/verify",
    response_model=PurchasePaymentVerificationResponse,
)
def verify_purchase_payment(
    session_id: str,
    request: PaymentVerificationRequest,
    session: Session = Depends(get_session),
):
    snapshot = session.get(PurchaseSessionState, session_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Purchase session not found")

    order = session.exec(
        select(Order).where(
            Order.session_id == session_id,
            Order.razorpay_order_id == request.razorpay_order_id,
        )
    ).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Razorpay order not found for purchase session")

    if order.status == "PAID":
        return PurchasePaymentVerificationResponse(
            session_id=session_id,
            status="PAID",
            razorpay_order_id=order.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            message="Payment already reconciled.",
        )

    secret = get_setting("RAZORPAY_KEY_SECRET")
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="RAZORPAY_KEY_SECRET must be configured",
        )

    try:
        verify_payment_signature(
            order_id=order.razorpay_order_id,
            payment_id=request.razorpay_payment_id,
            signature=request.razorpay_signature,
            secret=secret,
        )

        existing_payment = session.exec(
            select(Payment).where(
                Payment.order_id == order.id,
                Payment.razorpay_payment_id == request.razorpay_payment_id,
            )
        ).first()

        if existing_payment is None:
            session.add(
                Payment(
                    order_id=order.id,
                    razorpay_payment_id=request.razorpay_payment_id,
                    status="PENDING",
                    method="unknown",
                )
            )
            session.commit()

        result = reconcile_payment(
            session=session,
            razorpay_client=get_razorpay_client(),
            order=order,
            expected_amount_paise=order.amount_paise,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    snapshot.status = "PAID" if result["status"] == "PAID" else "PAYMENT_PENDING"
    session.add(snapshot)
    session.commit()

    return PurchasePaymentVerificationResponse(
        session_id=session_id,
        status=result["status"],
        razorpay_order_id=order.razorpay_order_id,
        razorpay_payment_id=result.get("razorpay_payment_id") or request.razorpay_payment_id,
        message=(
            "Payment signature verified and order reconciled."
            if result["status"] == "PAID"
            else "Payment signature verified; Razorpay has not reported a captured payment yet."
        ),
    )


# ===== Payment Retry Endpoint (Fixed) =====

@app.post(
    "/api/purchases/{session_id}/retry",
    response_model=PurchaseRetryResponse,
)
def retry_purchase(
    session_id: str,
    session: Session = Depends(get_session),
):
    snapshot = session.get(PurchaseSessionState, session_id)

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="Purchase session not found",
        )

    # Find the most recent FAILED payment order, not simply the latest order.
    # After a successful retry creation, the newest order is CREATED, while
    # the original order remains PAYMENT_FAILED.
    failed_order = session.exec(
        select(Order)
        .where(
            Order.session_id == session_id,
            Order.status == "PAYMENT_FAILED",
        )
        .order_by(Order.id.desc())
    ).first()

    if failed_order is None:
        raise HTTPException(
            status_code=409,
            detail="No order is available for retry: no failed payment order exists",
        )

    # Count retry attempts already started for this purchase session.
    retry_events = session.exec(
        select(AuditEvent).where(
            AuditEvent.session_id == session_id,
            AuditEvent.event_type == "retry_started",
        )
    ).all()

    retry_count = len(retry_events)

    # Check configuration before calling Razorpay.
    key_id = get_setting("RAZORPAY_KEY_ID")
    if not key_id:
        raise HTTPException(
            status_code=500,
            detail="RAZORPAY_KEY_ID must be configured",
        )

    try:
        retry = retry_order(
            session=session,
            razorpay_client=get_razorpay_client(),
            failed_order=failed_order,
            retry_count=retry_count,
            idempotency_key=(
                f"uplift-retry-{session_id}-{retry_count + 1}"
            ),
            agent_run_id=f"retry-{session_id}",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    snapshot.status = "ORDER_CREATED"
    session.add(snapshot)
    session.commit()

    return PurchaseRetryResponse(
        session_id=session_id,
        status=snapshot.status,
        retry_count=retry_count + 1,
        amount_paise=retry.amount_paise,
        currency=retry.currency,
        order_id=retry.razorpay_order_id,
        local_order_id=retry.id,
        key_id=key_id,
    )


@app.post("/test/razorpay/order")
def create_test_razorpay_order(
    session: Session = Depends(get_session),
):
    amount_paise = 89900
    session_id = f"test-session-{uuid4().hex}"
    idempotency_key = f"test-{uuid4().hex}"

    order = create_order(
        session=session,
        razorpay_client=get_razorpay_client(),
        session_id=session_id,
        amount_paise=amount_paise,
        idempotency_key=idempotency_key,
    )

    key_id = get_setting("RAZORPAY_KEY_ID")

    if not key_id:
        raise RuntimeError("RAZORPAY_KEY_ID must be configured.")

    return {
        "order_id": order.razorpay_order_id,
        "amount_paise": order.amount_paise,
        "currency": order.currency,
        "key_id": key_id,
        "local_order_id": order.id,
    }


@app.post("/test/razorpay/verify")
def verify_test_razorpay_payment(
    request: PaymentVerificationRequest,
    session: Session = Depends(get_session),
):
    order = session.exec(
        select(Order).where(
            Order.razorpay_order_id == request.razorpay_order_id
        )
    ).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Local order not found")

    if not order.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Order has no Razorpay order ID")

    if order.status == "PAID":
        raise HTTPException(status_code=409, detail="Order is already paid")

    secret = get_setting("RAZORPAY_KEY_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="RAZORPAY_KEY_SECRET must be configured")

    verify_payment_signature(
        order_id=order.razorpay_order_id,
        payment_id=request.razorpay_payment_id,
        signature=request.razorpay_signature,
        secret=secret,
    )

    existing_payment = session.exec(
        select(Payment).where(
            Payment.order_id == order.id,
            Payment.razorpay_payment_id == request.razorpay_payment_id,
        )
    ).first()

    if existing_payment is None:
        payment = Payment(
            order_id=order.id,
            razorpay_payment_id=request.razorpay_payment_id,
            status="PENDING",
            method="card",
        )
        session.add(payment)
        session.commit()

    return reconcile_payment(
        session=session,
        razorpay_client=get_razorpay_client(),
        order=order,
        expected_amount_paise=order.amount_paise,
    )


@app.post("/test/razorpay/failure")
def record_test_razorpay_failure(
    request: PaymentFailureRequest,
    session: Session = Depends(get_session),
):
    order = session.exec(
        select(Order).where(
            Order.razorpay_order_id == request.razorpay_order_id
        )
    ).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Local order not found")

    if order.status == "PAID":
        raise HTTPException(status_code=409, detail="Order is already paid")

    razorpay_client = get_razorpay_client()
    result = razorpay_client.order.payments(request.razorpay_order_id)

    failed_payment = next(
        (
            payment
            for payment in result.get("items", [])
            if payment.get("id") == request.razorpay_payment_id
            and payment.get("status") == "failed"
        ),
        None,
    )

    if failed_payment is None:
        raise HTTPException(
            status_code=400,
            detail="Failed payment was not confirmed by Razorpay",
        )

    if failed_payment.get("amount") != order.amount_paise:
        raise HTTPException(
            status_code=400,
            detail="Failed payment amount does not match order amount",
        )

    failure_reason = (
        failed_payment.get("error_reason")
        or failed_payment.get("error_description")
        or "Payment failed"
    )

    payment = record_payment_failure(
        session=session,
        order=order,
        razorpay_payment_id=request.razorpay_payment_id,
        method=failed_payment.get("method", "unknown"),
        failure_reason=failure_reason,
    )

    # Update the purchase session state to PAYMENT_FAILED
    snapshot = session.get(PurchaseSessionState, order.session_id)

    if snapshot is not None:
        snapshot.status = "PAYMENT_FAILED"
        session.add(snapshot)
        session.commit()

    return {
        "status": "PAYMENT_FAILED",
        "order_id": order.razorpay_order_id,
        "payment_id": payment.razorpay_payment_id,
        "failure_reason": payment.failure_reason,
    }



@app.get("/api/experiment/summary", response_model=ExperimentSummaryResponse)
def get_experiment_summary(
    session: Session = Depends(get_session),
):
    """
    Summarize measured Test Mode outcomes.

    When explicit ExperimentObservation rows exist, they define the arms.
    Otherwise, existing sessions are grouped observationally by whether the
    server-computed offer contained an upsell. This fallback is intentionally
    labeled as observational and must not be interpreted as causal A/B evidence.
    """
    observations = session.exec(select(ExperimentObservation)).all()

    purchase_sessions = session.exec(select(PurchaseSessionState)).all()
    orders = session.exec(select(Order)).all()
    approvals = session.exec(select(PurchaseApproval)).all()
    audit_events = session.exec(select(AuditEvent)).all()

    observation_by_session = {item.session_id: item for item in observations}
    arm_by_session: dict[str, str] = {}

    for purchase_session in purchase_sessions:
        observation = observation_by_session.get(purchase_session.id)
        if observation is not None:
            arm_by_session[purchase_session.id] = observation.arm
            continue

        try:
            offer = PurchaseOffer.model_validate_json(purchase_session.offer_json)
        except ValueError:
            continue

        arm_by_session[purchase_session.id] = (
            "treatment" if offer.upsell_product_id is not None else "control"
        )

    latest_orders: dict[str, Order] = {}
    for order in sorted(
        orders,
        key=lambda item: (
            item.created_at,
            item.id if item.id is not None else -1,
        ),
    ):
        latest_orders[order.session_id] = order

    def arm_metrics(arm: str) -> ExperimentArmMetrics:
        arm_sessions = [
            purchase_session
            for purchase_session in purchase_sessions
            if arm_by_session.get(purchase_session.id) == arm
        ]
        successful_orders = [
            latest_orders[purchase_session.id]
            for purchase_session in arm_sessions
            if purchase_session.id in latest_orders
            and latest_orders[purchase_session.id].status == "PAID"
        ]
        revenue_paise = sum(order.amount_paise for order in successful_orders)
        aov_paise = (
            round(revenue_paise / len(successful_orders))
            if successful_orders
            else 0
        )
        conversion_pct = (
            round(len(successful_orders) / len(arm_sessions) * 100, 1)
            if arm_sessions
            else 0.0
        )
        return ExperimentArmMetrics(
            sessions=len(arm_sessions),
            successful_orders=len(successful_orders),
            revenue_paise=revenue_paise,
            aov_paise=aov_paise,
            conversion_pct=conversion_pct,
        )

    treatment = arm_metrics("treatment")
    control = arm_metrics("control")

    aov_lift_pct = (
        round((treatment.aov_paise - control.aov_paise) / control.aov_paise * 100, 1)
        if control.aov_paise
        else None
    )

    comparable_sessions = min(treatment.sessions, control.sessions)
    revenue_delta_per_session_paise = (
        round(
            (
                treatment.revenue_paise / treatment.sessions
                if treatment.sessions
                else 0
            )
            - (
                control.revenue_paise / control.sessions
                if control.sessions
                else 0
            ),
            1,
        )
        if comparable_sessions
        else None
    )

    treatment_offers = 0
    treatment_accepts = 0
    for purchase_session in purchase_sessions:
        if arm_by_session.get(purchase_session.id) != "treatment":
            continue
        try:
            offer = PurchaseOffer.model_validate_json(purchase_session.offer_json)
        except ValueError:
            continue
        if offer.upsell_product_id is None:
            continue
        treatment_offers += 1
        approval = next(
            (
                item
                for item in approvals
                if item.session_id == purchase_session.id
                and item.approved
            ),
            None,
        )
        if approval is not None:
            treatment_accepts += 1

    upsell_acceptance_pct = (
        round(treatment_accepts / treatment_offers * 100, 1)
        if treatment_offers
        else 0.0
    )

    blocked_unsafe_actions = sum(
        1
        for event in audit_events
        if event.decision == "REJECTED"
        and event.event_type not in {"payment_failed"}
    )

    initial_failures = {
        event.session_id
        for event in audit_events
        if event.event_type == "payment_failed"
    }
    retried_and_recovered = {
        session_id
        for session_id in initial_failures
        if any(
            event.session_id == session_id
            and event.event_type == "retry_started"
            for event in audit_events
        )
        and session_id in latest_orders
        and latest_orders[session_id].status == "PAID"
    }
    payment_recovery_pct = (
        round(len(retried_and_recovered) / len(initial_failures) * 100, 1)
        if initial_failures
        else None
    )

    methodology = (
        "Explicitly assigned control/treatment observations."
        if observations
        else (
            "Observational fallback: sessions are grouped by the presence "
            "of a server-computed upsell. This is measured Test Mode data, "
            "not a randomized or causal A/B result."
        )
    )

    return ExperimentSummaryResponse(
        methodology=methodology,
        treatment=treatment,
        control=control,
        aov_lift_pct=aov_lift_pct,
        revenue_delta_per_session_paise=revenue_delta_per_session_paise,
        upsell_acceptance_pct=upsell_acceptance_pct,
        blocked_unsafe_actions=blocked_unsafe_actions,
        payment_recovery_pct=payment_recovery_pct,
    )


@app.get("/api/audit", response_model=AuditLogResponse)
def get_audit_log(
    session: Session = Depends(get_session),
):
    records = session.exec(
        select(AuditEvent)
        .order_by(AuditEvent.timestamp.desc(), AuditEvent.id.desc())
    ).all()

    events: list[AuditLogEvent] = []

    for event in records:
        try:
            payload = json.loads(event.payload_json)
        except (TypeError, json.JSONDecodeError):
            payload = {
                "raw": event.payload_json,
            }

        events.append(
            AuditLogEvent(
                id=event.id,
                timestamp=event.timestamp.isoformat(),
                session_id=event.session_id,
                actor_type=event.actor_type,
                action_id=event.action_id,
                event_type=event.event_type,
                decision=event.decision,
                reason=event.reason,
                policy_version=event.policy_version,
                buyer_budget_paise=event.buyer_budget_paise,
                razorpay_order_id=event.razorpay_order_id,
                razorpay_payment_id=event.razorpay_payment_id,
                payload=payload,
            )
        )

    return AuditLogResponse(events=events)
