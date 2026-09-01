import pytest

from apps.api.razorpay_client.service import handle_payment_failure
from unittest.mock import Mock
from sqlmodel import select

from apps.api.models import Order, AuditEvent
from apps.api.razorpay_client.service import retry_order


def test_payment_failure_allows_one_retry():
    result = handle_payment_failure(
        retry_count=0,
        failure_reason="Payment declined",
    )

    assert result["status"] == "RETRY_AVAILABLE"
    assert result["retry_count"] == 1


def test_payment_failure_is_exhausted_after_one_retry():
    result = handle_payment_failure(
        retry_count=1,
        failure_reason="Payment declined again",
    )

    assert result["status"] == "RETRY_EXHAUSTED"
    assert result["retry_count"] == 1


def test_payment_failure_rejects_negative_retry_count():
    with pytest.raises(ValueError, match="retry_count cannot be negative"):
        handle_payment_failure(
            retry_count=-1,
            failure_reason="Payment declined",
        )


def test_payment_failure_returns_failure_reason():
    result = handle_payment_failure(
        retry_count=0,
        failure_reason="Payment declined",
    )

    assert result["status"] == "RETRY_AVAILABLE"
    assert result["retry_count"] == 1
    assert result["failure_reason"] == "Payment declined"


def test_payment_failure_exhaustion_preserves_failure_reason():
    result = handle_payment_failure(
        retry_count=1,
        failure_reason="Insufficient funds",
    )

    assert result["status"] == "RETRY_EXHAUSTED"
    assert result["retry_count"] == 1
    assert result["failure_reason"] == "Insufficient funds"


def test_payment_failure_does_not_allow_second_retry():
    result = handle_payment_failure(
        retry_count=2,
        failure_reason="Payment declined again",
    )

    assert result["status"] == "RETRY_EXHAUSTED"
    assert result["retry_count"] == 2

def test_retry_order_creates_fresh_razorpay_order(session):
    razorpay_client = Mock()

    razorpay_client.order.create.return_value = {
        "id": "order_retry_001",
    }

    failed_order = Order(
        session_id="session-001",
        amount_paise=249800,
        currency="INR",
        status="PAYMENT_FAILED",
        razorpay_order_id="order_failed_001",
        idempotency_key="idem_failed_001",
    )

    session.add(failed_order)
    session.commit()
    session.refresh(failed_order)

    retry = retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_001",
    )

    assert retry.status == "CREATED"
    assert retry.razorpay_order_id == "order_retry_001"
    assert retry.idempotency_key == "idem_retry_001"
    assert retry.razorpay_order_id != failed_order.razorpay_order_id

    razorpay_client.order.create.assert_called_once()

def test_retry_order_rejects_retry_after_retry_limit(session):
    razorpay_client = Mock()

    failed_order = Order(
        session_id="session-002",
        amount_paise=249800,
        currency="INR",
        status="PAYMENT_FAILED",
        razorpay_order_id="order_failed_002",
        idempotency_key="idem_failed_002",
    )

    session.add(failed_order)
    session.commit()
    session.refresh(failed_order)

    with pytest.raises(ValueError, match="Payment retry limit exhausted"):
        retry_order(
            session=session,
            razorpay_client=razorpay_client,
            failed_order=failed_order,
            retry_count=1,
            idempotency_key="idem_retry_002",
        )

    razorpay_client.order.create.assert_not_called()

def test_retry_order_rejects_non_failed_order(session):
    razorpay_client = Mock()

    created_order = Order(
        session_id="session-003",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_created_001",
        idempotency_key="idem_created_001",
    )

    session.add(created_order)
    session.commit()
    session.refresh(created_order)

    with pytest.raises(ValueError, match="Only failed orders can be retried"):
        retry_order(
            session=session,
            razorpay_client=razorpay_client,
            failed_order=created_order,
            retry_count=0,
            idempotency_key="idem_retry_003",
        )

    razorpay_client.order.create.assert_not_called()

def test_retry_order_preserves_authoritative_amount(session):
    razorpay_client = Mock()

    razorpay_client.order.create.return_value = {
        "id": "order_retry_004",
    }

    failed_order = Order(
        session_id="session-004",
        amount_paise=249800,
        currency="INR",
        status="PAYMENT_FAILED",
        razorpay_order_id="order_failed_004",
        idempotency_key="idem_failed_004",
    )

    session.add(failed_order)
    session.commit()
    session.refresh(failed_order)

    retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_004",
    )

    razorpay_client.order.create.assert_called_once_with(
        data={
            "amount": 249800,
            "currency": "INR",
            "receipt": "idem_retry_004",
        }
    )

def test_failed_order_can_be_persisted_with_failure_status(session):
    order = Order(
        session_id="session-005",
        amount_paise=249800,
        currency="INR",
        status="PAYMENT_FAILED",
        razorpay_order_id="order_failed_005",
        idempotency_key="idem_failed_005",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    assert order.status == "PAYMENT_FAILED"
    assert order.razorpay_order_id == "order_failed_005"


def test_retry_order_does_not_modify_failed_order(session):
    razorpay_client = Mock()

    razorpay_client.order.create.return_value = {
        "id": "order_retry_006",
    }

    failed_order = Order(
        session_id="session-006",
        amount_paise=249800,
        currency="INR",
        status="PAYMENT_FAILED",
        razorpay_order_id="order_failed_006",
        idempotency_key="idem_failed_006",
    )

    session.add(failed_order)
    session.commit()
    session.refresh(failed_order)

    retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_006",
    )

    session.refresh(failed_order)

    assert failed_order.status == "PAYMENT_FAILED"
    assert failed_order.razorpay_order_id == "order_failed_006"
    assert failed_order.idempotency_key == "idem_failed_006"


def test_retry_order_creates_exactly_one_new_local_order(session):
    razorpay_client = Mock()

    razorpay_client.order.create.return_value = {
        "id": "order_retry_007",
    }

    failed_order = Order(
        session_id="session-007",
        amount_paise=249800,
        currency="INR",
        status="PAYMENT_FAILED",
        razorpay_order_id="order_failed_007",
        idempotency_key="idem_failed_007",
    )

    session.add(failed_order)
    session.commit()
    session.refresh(failed_order)

    retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_007",
    )

    orders = session.exec(
        select(Order).where(Order.session_id == "session-007")
    ).all()

    assert len(orders) == 2

    retry_orders = [
        order
        for order in orders
        if order.idempotency_key == "idem_retry_007"
    ]

    assert len(retry_orders) == 1
    assert retry_orders[0].razorpay_order_id == "order_retry_007"

def test_record_payment_failure_updates_order_and_creates_payment(session):
    from apps.api.razorpay_client.service import record_payment_failure

    order = Order(
        session_id="session-008",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_008",
        idempotency_key="idem_008",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    payment = record_payment_failure(
        session=session,
        order=order,
        razorpay_payment_id="pay_008",
        method="upi",
        failure_reason="Payment declined",
    )

    session.refresh(order)
    session.refresh(payment)

    assert order.status == "PAYMENT_FAILED"
    assert payment.order_id == order.id
    assert payment.razorpay_payment_id == "pay_008"
    assert payment.status == "FAILED"
    assert payment.method == "upi"


def test_record_payment_failure_preserves_failure_reason(session):
    from apps.api.razorpay_client.service import record_payment_failure

    order = Order(
        session_id="session-009",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_009",
        idempotency_key="idem_009",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    payment = record_payment_failure(
        session=session,
        order=order,
        razorpay_payment_id="pay_009",
        method="upi",
        failure_reason="Insufficient funds",
    )

    assert payment.status == "FAILED"
    assert payment.failure_reason == "Insufficient funds"

def test_record_payment_failure_requires_payment_id(session):
    from apps.api.razorpay_client.service import record_payment_failure

    order = Order(
        session_id="session-010",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_010",
        idempotency_key="idem_010",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    with pytest.raises(ValueError, match="razorpay_payment_id"):
        record_payment_failure(
            session=session,
            order=order,
            razorpay_payment_id="",
            method="upi",
            failure_reason="Payment declined",
        )


def test_record_payment_failure_requires_failure_reason(session):
    from apps.api.razorpay_client.service import record_payment_failure

    order = Order(
        session_id="session-011",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_011",
        idempotency_key="idem_011",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    with pytest.raises(ValueError, match="failure_reason"):
        record_payment_failure(
            session=session,
            order=order,
            razorpay_payment_id="pay_011",
            method="upi",
            failure_reason="",
        )


def test_record_payment_failure_requires_payment_method(session):
    from apps.api.razorpay_client.service import record_payment_failure

    order = Order(
        session_id="session-012",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_012",
        idempotency_key="idem_012",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    with pytest.raises(ValueError, match="method"):
        record_payment_failure(
            session=session,
            order=order,
            razorpay_payment_id="pay_012",
            method="",
            failure_reason="Payment declined",
        )

def test_record_payment_failure_creates_payment_failed_audit_event(session):
    from apps.api.audit.service import record_audit_event
    from apps.api.razorpay_client.service import record_payment_failure

    order = Order(
        session_id="session-013",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_013",
        idempotency_key="idem_013",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    payment = record_payment_failure(
        session=session,
        order=order,
        razorpay_payment_id="pay_013",
        method="upi",
        failure_reason="Payment declined",
    )

    event = record_audit_event(
        session=session,
        agent_run_id="run-013",
        session_id=order.session_id,
        actor_type="SYSTEM",
        action_id="payment-failure",
        event_type="payment_failed",
        reason=payment.failure_reason,
        payload={
            "order_id": order.id,
            "razorpay_payment_id": payment.razorpay_payment_id,
        },
    )

    assert event.event_type == "payment_failed"
    assert event.reason == "Payment declined"


def test_retry_started_audit_event_is_recorded(session):
    from apps.api.audit.service import record_audit_event

    event = record_audit_event(
        session=session,
        agent_run_id="run-014",
        session_id="session-014",
        actor_type="SYSTEM",
        action_id="retry-014",
        event_type="retry_started",
        payload={
            "retry_count": 1,
            "previous_order_id": "order_failed_014",
            "new_idempotency_key": "idem_retry_014",
        },
    )

    assert event.event_type == "retry_started"
    assert event.payload_json is not None


def test_retry_exhausted_audit_event_is_recorded(session):
    from apps.api.audit.service import record_audit_event

    event = record_audit_event(
        session=session,
        agent_run_id="run-015",
        session_id="session-015",
        actor_type="SYSTEM",
        action_id="retry-015",
        event_type="retry_exhausted",
        reason="Payment retry limit exhausted",
        payload={
            "retry_count": 1,
        },
    )

    assert event.event_type == "retry_exhausted"
    assert event.reason == "Payment retry limit exhausted"

def test_record_payment_failure_writes_payment_failed_audit_event(session):
    from apps.api.razorpay_client.service import record_payment_failure

    order = Order(
        session_id="session-016",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_016",
        idempotency_key="idem_016",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    record_payment_failure(
        session=session,
        order=order,
        razorpay_payment_id="pay_016",
        method="upi",
        failure_reason="Payment declined",
        agent_run_id="run-016",
    )

    events = session.exec(
        select(AuditEvent).where(
            AuditEvent.session_id == "session-016"
        )
    ).all()

    assert len(events) == 1
    assert events[0].event_type == "payment_failed"
    assert events[0].agent_run_id == "run-016"
    assert events[0].razorpay_order_id == "order_016"
    assert events[0].razorpay_payment_id == "pay_016"
    assert events[0].reason == "Payment declined"


def test_retry_order_writes_retry_started_audit_event(session):
    from apps.api.razorpay_client.service import retry_order

    razorpay_client = Mock()

    razorpay_client.order.create.return_value = {
        "id": "order_retry_017",
    }

    failed_order = Order(
        session_id="session-017",
        amount_paise=249800,
        currency="INR",
        status="PAYMENT_FAILED",
        razorpay_order_id="order_failed_017",
        idempotency_key="idem_failed_017",
    )

    session.add(failed_order)
    session.commit()
    session.refresh(failed_order)

    retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_017",
        agent_run_id="run-017",
    )

    events = session.exec(
        select(AuditEvent).where(
            AuditEvent.session_id == "session-017"
        )
    ).all()

    assert len(events) == 1
    assert events[0].event_type == "retry_started"
    assert events[0].agent_run_id == "run-017"


def test_retry_order_writes_retry_exhausted_audit_event(session):
    from apps.api.razorpay_client.service import retry_order

    razorpay_client = Mock()

    failed_order = Order(
        session_id="session-018",
        amount_paise=249800,
        currency="INR",
        status="PAYMENT_FAILED",
        razorpay_order_id="order_failed_018",
        idempotency_key="idem_failed_018",
    )

    session.add(failed_order)
    session.commit()
    session.refresh(failed_order)

    with pytest.raises(ValueError, match="Payment retry limit exhausted"):
        retry_order(
            session=session,
            razorpay_client=razorpay_client,
            failed_order=failed_order,
            retry_count=1,
            idempotency_key="idem_retry_018",
            agent_run_id="run-018",
        )

    events = session.exec(
        select(AuditEvent).where(
            AuditEvent.session_id == "session-018"
        )
    ).all()

    assert len(events) == 1
    assert events[0].event_type == "retry_exhausted"
    assert events[0].agent_run_id == "run-018"

def test_retry_order_records_retry_started_before_second_attempt(session):
    from apps.api.razorpay_client.service import retry_order

    razorpay_client = Mock()
    razorpay_client.order.create.return_value = {
        "id": "order_retry_019",
    }

    failed_order = Order(
        session_id="session-019",
        amount_paise=249800,
        currency="INR",
        status="PAYMENT_FAILED",
        razorpay_order_id="order_failed_019",
        idempotency_key="idem_failed_019",
    )

    session.add(failed_order)
    session.commit()
    session.refresh(failed_order)

    retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_019",
        agent_run_id="run-019",
    )

    events = session.exec(
        select(AuditEvent)
        .where(AuditEvent.session_id == "session-019")
    ).all()

    assert len(events) == 1
    assert events[0].event_type == "retry_started"


def test_second_payment_failure_records_retry_failed(session):
    from apps.api.razorpay_client.service import record_payment_failure

    order = Order(
        session_id="session-020",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_020",
        idempotency_key="idem_020",
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    record_payment_failure(
        session=session,
        order=order,
        razorpay_payment_id="pay_020",
        method="upi",
        failure_reason="Payment declined again",
        agent_run_id="run-020",
    )

    retry_result = handle_payment_failure(
        retry_count=1,
        failure_reason="Payment declined again",
    )

    assert retry_result["status"] == "RETRY_EXHAUSTED"

    events = session.exec(
        select(AuditEvent)
        .where(AuditEvent.session_id == "session-020")
    ).all()

    assert any(event.event_type == "payment_failed" for event in events)