import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from apps.api.database import create_db_and_tables, get_session
from apps.api.models import Order, Payment
from apps.api.razorpay_client.client import get_razorpay_client
from apps.api.razorpay_client.reconciliation import reconcile_payment
from apps.api.razorpay_client.service import create_order, record_payment_failure
from apps.api.razorpay_client.verification import verify_payment_signature


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Uplift API",
    lifespan=lifespan,
)


class PaymentVerificationRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


class PaymentFailureRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


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

    key_id = os.getenv("RAZORPAY_KEY_ID")

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
        raise HTTPException(
            status_code=404,
            detail="Local order not found",
        )

    if not order.razorpay_order_id:
        raise HTTPException(
            status_code=400,
            detail="Order has no Razorpay order ID",
        )

    if order.status == "PAID":
        raise HTTPException(
            status_code=409,
            detail="Order is already paid",
        )

    secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not secret:
        raise HTTPException(
            status_code=500,
            detail="RAZORPAY_KEY_SECRET must be configured",
        )

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

    result = reconcile_payment(
        session=session,
        razorpay_client=get_razorpay_client(),
        order=order,
        expected_amount_paise=order.amount_paise,
    )

    return result


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
        raise HTTPException(
            status_code=404,
            detail="Local order not found",
        )

    if order.status == "PAID":
        raise HTTPException(
            status_code=409,
            detail="Order is already paid",
        )

    # Confirm the payment exists in Razorpay and is actually failed.
    razorpay_client = get_razorpay_client()

    result = razorpay_client.order.payments(
        request.razorpay_order_id
    )

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

    return {
        "status": "PAYMENT_FAILED",
        "order_id": order.razorpay_order_id,
        "payment_id": payment.razorpay_payment_id,
        "failure_reason": payment.failure_reason,
    }