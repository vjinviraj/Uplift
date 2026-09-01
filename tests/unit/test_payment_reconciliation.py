from unittest.mock import Mock

import pytest

from apps.api.razorpay_client.reconciliation import reconcile_payment
from apps.api.models import Order, Payment


def test_reconcile_payment_succeeds_when_captured_payment_exists(session):
    razorpay_client = Mock()

    razorpay_client.order.payments.return_value = {
        "items": [
            {
                "id": "pay_001",
                "status": "captured",
                "amount": 249800,
            }
        ]
    }

    order = Order(
        session_id="session-001",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_001",
        idempotency_key="idem_001",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    payment = Payment(
        order_id=order.id,
        razorpay_payment_id="pay_001",
        status="PENDING",
        method="upi",
    )

    session.add(payment)
    session.commit()

    result = reconcile_payment(
        session=session,
        razorpay_client=razorpay_client,
        order=order,
        expected_amount_paise=249800,
    )

    assert result["status"] == "PAID"
    assert result["razorpay_payment_id"] == "pay_001"


def test_reconcile_payment_fails_when_no_captured_payment_exists(session):
    razorpay_client = Mock()

    razorpay_client.order.payments.return_value = {
        "items": [
            {
                "id": "pay_002",
                "status": "failed",
                "amount": 249800,
            }
        ]
    }

    order = Order(
        session_id="session-002",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_002",
        idempotency_key="idem_002",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    result = reconcile_payment(
        session=session,
        razorpay_client=razorpay_client,
        order=order,
        expected_amount_paise=249800,
    )

    assert result["status"] == "NOT_PAID"


def test_reconcile_payment_rejects_wrong_captured_amount(session):
    razorpay_client = Mock()

    razorpay_client.order.payments.return_value = {
        "items": [
            {
                "id": "pay_003",
                "status": "captured",
                "amount": 199800,
            }
        ]
    }

    order = Order(
        session_id="session-003",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_003",
        idempotency_key="idem_003",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    with pytest.raises(ValueError, match="Payment amount mismatch"):
        reconcile_payment(
            session=session,
            razorpay_client=razorpay_client,
            order=order,
            expected_amount_paise=249800,
        )


def test_reconcile_payment_handles_empty_payment_list(session):
    razorpay_client = Mock()

    razorpay_client.order.payments.return_value = {
        "items": []
    }

    order = Order(
        session_id="session-004",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_004",
        idempotency_key="idem_004",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    result = reconcile_payment(
        session=session,
        razorpay_client=razorpay_client,
        order=order,
        expected_amount_paise=249800,
    )

    assert result["status"] == "NOT_PAID"


def test_reconcile_payment_ignores_failed_attempt_before_captured_payment(session):
    razorpay_client = Mock()

    razorpay_client.order.payments.return_value = {
        "items": [
            {
                "id": "pay_failed_005",
                "status": "failed",
                "amount": 249800,
            },
            {
                "id": "pay_captured_005",
                "status": "captured",
                "amount": 249800,
            },
        ]
    }

    order = Order(
        session_id="session-005",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_005",
        idempotency_key="idem_005",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    payment = Payment(
        order_id=order.id,
        razorpay_payment_id="pay_captured_005",
        status="PENDING",
        method="upi",
    )

    session.add(payment)
    session.commit()

    result = reconcile_payment(
        session=session,
        razorpay_client=razorpay_client,
        order=order,
        expected_amount_paise=249800,
    )

    assert result["status"] == "PAID"
    assert result["razorpay_payment_id"] == "pay_captured_005"


def test_reconcile_payment_rejects_wrong_captured_payment_before_valid_one(session):
    razorpay_client = Mock()

    razorpay_client.order.payments.return_value = {
        "items": [
            {
                "id": "pay_wrong_006",
                "status": "captured",
                "amount": 199800,
            },
            {
                "id": "pay_correct_006",
                "status": "captured",
                "amount": 249800,
            },
        ]
    }

    order = Order(
        session_id="session-006",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_006",
        idempotency_key="idem_006",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    payment = Payment(
        order_id=order.id,
        razorpay_payment_id="pay_correct_006",
        status="PENDING",
        method="upi",
    )

    session.add(payment)
    session.commit()

    result = reconcile_payment(
        session=session,
        razorpay_client=razorpay_client,
        order=order,
        expected_amount_paise=249800,
    )

    assert result["status"] == "PAID"
    assert result["razorpay_payment_id"] == "pay_correct_006"


def test_reconcile_payment_writes_payment_reconciled_audit_event(session):
    from apps.api.audit.service import record_audit_event

    event = record_audit_event(
        session=session,
        agent_run_id="run-reconcile-001",
        session_id="session-reconcile-001",
        actor_type="SYSTEM",
        action_id="payment-reconciliation",
        event_type="payment_reconciled",
        reason="Captured payment matches authoritative order amount",
        razorpay_order_id="order-reconcile-001",
        razorpay_payment_id="pay-reconcile-001",
    )

    assert event.event_type == "payment_reconciled"
    assert event.razorpay_order_id == "order-reconcile-001"
    assert event.razorpay_payment_id == "pay-reconcile-001"


def test_reconcile_payment_marks_local_payment_verified(session):
    from datetime import datetime

    razorpay_client = Mock()

    razorpay_client.order.payments.return_value = {
        "items": [
            {
                "id": "pay_007",
                "status": "captured",
                "amount": 249800,
            }
        ]
    }

    order = Order(
        session_id="session-007",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_007",
        idempotency_key="idem_007",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    payment = Payment(
        order_id=order.id,
        razorpay_payment_id="pay_007",
        status="PENDING",
        method="upi",
    )

    session.add(payment)
    session.commit()

    result = reconcile_payment(
        session=session,
        razorpay_client=razorpay_client,
        order=order,
        expected_amount_paise=249800,
    )

    session.refresh(payment)

    assert result["status"] == "PAID"
    assert payment.status == "SUCCESS"
    assert payment.verified_at is not None
    assert isinstance(payment.verified_at, datetime)