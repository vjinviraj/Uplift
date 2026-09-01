import hashlib
import hmac
import pytest

from apps.api.razorpay_client.verification import verify_payment_signature

from unittest.mock import Mock

from apps.api.razorpay_client.service import (
    create_order,
    record_payment_failure,
    retry_order,
)

from sqlmodel import select

from apps.api.models import AuditEvent, Order, Payment
from apps.api.razorpay_client.service import handle_payment_failure

def test_day2_successful_payment_flow(session):
    razorpay_client = Mock()

    razorpay_client.order.create.return_value = {
        "id": "order_e2e_001",
    }

    order = create_order(
        session=session,
        razorpay_client=razorpay_client,
        session_id="session-e2e-001",
        amount_paise=249800,
        idempotency_key="idem-e2e-001",
    )

    assert order.status == "CREATED"
    assert order.amount_paise == 249800
    assert order.razorpay_order_id == "order_e2e_001"

    session.add(
        Payment(
            order_id=order.id,
            razorpay_payment_id="pay-e2e-001",
            status="SUCCESS",
            method="upi",
        )
    )
    session.commit()

    payment = session.exec(
        select(Payment).where(Payment.order_id == order.id)
    ).one()

    assert payment.status == "SUCCESS"
    assert payment.failure_reason is None

def test_day2_failure_retry_flow(session):
    razorpay_client = Mock()

    razorpay_client.order.create.side_effect = [
        {"id": "order_e2e_failed"},
        {"id": "order_e2e_retry"},
    ]

    failed_order = create_order(
        session=session,
        razorpay_client=razorpay_client,
        session_id="session-e2e-002",
        amount_paise=249800,
        idempotency_key="idem-e2e-002",
    )

    payment = record_payment_failure(
        session=session,
        order=failed_order,
        razorpay_payment_id="pay-e2e-failed",
        method="upi",
        failure_reason="Payment declined",
        agent_run_id="run-e2e-002",
    )

    assert payment.status == "FAILED"
    assert failed_order.status == "PAYMENT_FAILED"

    retry = retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem-e2e-retry-002",
        agent_run_id="run-e2e-002",
    )

    assert retry.razorpay_order_id == "order_e2e_retry"
    assert retry.idempotency_key == "idem-e2e-retry-002"
    assert retry.amount_paise == failed_order.amount_paise

    retry_result = handle_payment_failure(
        retry_count=1,
        failure_reason="Payment declined again",
    )

    assert retry_result["status"] == "RETRY_EXHAUSTED"

def test_day2_signature_verification_accepts_valid_payment():
    order_id = "order_e2e_003"
    payment_id = "pay_e2e_003"
    secret = "test_secret"

    message = f"{order_id}|{payment_id}"

    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    assert verify_payment_signature(
        order_id=order_id,
        payment_id=payment_id,
        signature=signature,
        secret=secret,
    ) is True


def test_day2_signature_verification_rejects_tampered_payment():
    with pytest.raises(ValueError, match="Invalid payment signature"):
        verify_payment_signature(
            order_id="order_e2e_004",
            payment_id="pay_e2e_004",
            signature="tampered",
            secret="test_secret",
        )


def test_day2_signature_verification_rejects_missing_signature():
    with pytest.raises(ValueError, match="Payment signature is required"):
        verify_payment_signature(
            order_id="order_e2e_005",
            payment_id="pay_e2e_005",
            signature="",
            secret="test_secret",
        )