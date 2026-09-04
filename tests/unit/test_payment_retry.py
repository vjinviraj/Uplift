import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from apps.api.audit.service import record_audit_event
from apps.api.main import app
from apps.api.database import get_session
from apps.api.models import AuditEvent, Order, Payment, PurchaseSessionState
from apps.api.razorpay_client.service import retry_order
from apps.api.agents.schemas import PurchaseOffer, PurchaseRequest


def make_purchase_snapshot(session, session_id: str = "purchase-test-001"):
    request = PurchaseRequest(
        query="Genshin Impact",
        budget_paise=500_000,
        category_hint="Games",
        platform_hint=None,
        franchise_hint="Genshin Impact",
    )
    offer = PurchaseOffer(
        product_id="GAME-001",
        upsell_product_id="ACC-001",
        upsell_reason="Known compatible accessory",
        amount_paise=249_800,
        currency="INR",
        breakdown=[
            {
                "product_id": "GAME-001",
                "name": "Genshin Impact",
                "qty": 1,
                "unit_price_paise": 199_900,
                "line_total_paise": 199_900,
            },
            {
                "product_id": "ACC-001",
                "name": "Compatible Accessory",
                "qty": 1,
                "unit_price_paise": 49_900,
                "line_total_paise": 49_900,
            },
        ],
        policy_decision="ALLOW",
        policy_reason="Within policy",
        policy_version="api-v1",
    )

    snapshot = PurchaseSessionState(
        id=session_id,
        request_json=request.model_dump_json(),
        offer_json=offer.model_dump_json(),
        status="AWAITING_APPROVAL",
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def make_failed_order(
    session,
    session_id: str,
    *,
    status: str = "PAYMENT_FAILED",
    razorpay_order_id: str = "order_failed_001",
    amount_paise: int = 249_800,
    idempotency_key: str = "idem_failed_001",
):
    order = Order(
        session_id=session_id,
        amount_paise=amount_paise,
        currency="INR",
        status=status,
        razorpay_order_id=razorpay_order_id,
        idempotency_key=idempotency_key,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def override_get_session(session):
    def _override():
        yield session

    return _override


def test_failed_order_can_be_retried(session):
    razorpay_client = Mock()
    razorpay_client.order.create.return_value = {"id": "order_retry_001"}

    failed_order = make_failed_order(session, "session-001")

    retry = retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_001",
    )

    assert retry.status == "CREATED"
    assert retry.razorpay_order_id == "order_retry_001"


def test_retry_creates_a_different_razorpay_order_id(session):
    razorpay_client = Mock()
    razorpay_client.order.create.return_value = {"id": "order_retry_002"}

    failed_order = make_failed_order(
        session,
        "session-002",
        razorpay_order_id="order_failed_002",
    )

    retry = retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_002",
    )

    assert retry.razorpay_order_id != failed_order.razorpay_order_id


def test_retry_keeps_exactly_the_same_amount(session):
    razorpay_client = Mock()
    razorpay_client.order.create.return_value = {"id": "order_retry_003"}

    failed_order = make_failed_order(
        session,
        "session-003",
        amount_paise=899_00,
        razorpay_order_id="order_failed_003",
    )

    retry = retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_003",
    )

    assert retry.amount_paise == failed_order.amount_paise
    razorpay_client.order.create.assert_called_once_with(
        data={
            "amount": failed_order.amount_paise,
            "currency": "INR",
            "receipt": "idem_retry_003",
        }
    )


def test_failed_order_remains_payment_failed(session):
    razorpay_client = Mock()
    razorpay_client.order.create.return_value = {"id": "order_retry_004"}

    failed_order = make_failed_order(
        session,
        "session-004",
        razorpay_order_id="order_failed_004",
    )

    retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_004",
    )

    session.refresh(failed_order)

    assert failed_order.status == "PAYMENT_FAILED"


def test_retry_order_is_created(session):
    razorpay_client = Mock()
    razorpay_client.order.create.return_value = {"id": "order_retry_005"}

    failed_order = make_failed_order(session, "session-005")

    retry = retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_005",
    )

    assert retry.status == "CREATED"


def test_retry_started_audit_event_is_recorded(session):
    razorpay_client = Mock()
    razorpay_client.order.create.return_value = {"id": "order_retry_006"}

    failed_order = make_failed_order(
        session,
        "session-006",
        razorpay_order_id="order_failed_006",
    )

    retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_006",
        agent_run_id="retry-run-006",
    )

    events = session.exec(
        select(AuditEvent).where(
            AuditEvent.session_id == "session-006",
            AuditEvent.event_type == "retry_started",
        )
    ).all()

    assert len(events) == 1
    assert events[0].razorpay_order_id == "order_retry_006"
    assert json.loads(events[0].payload_json) == {
        "previous_order_id": "order_failed_006",
        "retry_order_id": "order_retry_006",
        "retry_count": 1,
    }


def test_retry_count_becomes_one(session):
    razorpay_client = Mock()
    razorpay_client.order.create.return_value = {"id": "order_retry_007"}

    failed_order = make_failed_order(
        session,
        "session-007",
        razorpay_order_id="order_failed_007",
    )

    retry_order(
        session=session,
        razorpay_client=razorpay_client,
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="idem_retry_007",
    )

    event = session.exec(
        select(AuditEvent).where(
            AuditEvent.session_id == "session-007",
            AuditEvent.event_type == "retry_started",
        )
    ).one()

    payload = json.loads(event.payload_json)
    assert payload["retry_count"] == 1


def test_second_retry_is_rejected(client_session, monkeypatch):
    client, session = client_session
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_dummy")
    snapshot = make_purchase_snapshot(session, "purchase-retry-limit")
    failed_order = make_failed_order(
        session,
        snapshot.id,
        razorpay_order_id="order_failed_limit",
        idempotency_key="idem_failed_limit",
    )

    razorpay_client = Mock()
    razorpay_client.order.create.return_value = {"id": "order_retry_limit"}
    monkeypatch.setattr(
        "apps.api.main.get_razorpay_client",
        lambda: razorpay_client,
    )

    first_response = client.post(f"/api/purchases/{snapshot.id}/retry")
    assert first_response.status_code == 200

    session.refresh(failed_order)
    assert failed_order.status == "PAYMENT_FAILED"

    second_response = client.post(f"/api/purchases/{snapshot.id}/retry")

    assert second_response.status_code == 409
    assert "retry limit" in second_response.json()["detail"].lower()


def test_retry_without_a_failed_order_is_rejected(client_session):
    client, session = client_session
    snapshot = make_purchase_snapshot(session, "purchase-no-failed-order")

    response = client.post(f"/api/purchases/{snapshot.id}/retry")

    assert response.status_code == 409
    assert "No order is available for retry" in response.json()["detail"]


def test_retry_of_paid_or_non_failed_order_is_rejected(client_session):
    client, session = client_session
    snapshot = make_purchase_snapshot(session, "purchase-non-failed")
    make_failed_order(
        session,
        snapshot.id,
        status="PAID",
        razorpay_order_id="order_paid_001",
        idempotency_key="idem_paid_001",
    )

    response = client.post(f"/api/purchases/{snapshot.id}/retry")

    assert response.status_code == 409
    assert "failed payment order" in response.json()["detail"].lower()


def test_missing_razorpay_key_id_returns_500(client_session, monkeypatch):
    client, session = client_session
    snapshot = make_purchase_snapshot(session, "purchase-missing-key")
    make_failed_order(
        session,
        snapshot.id,
        razorpay_order_id="order_failed_missing_key",
        idempotency_key="idem_failed_missing_key",
    )

    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)

    response = client.post(f"/api/purchases/{snapshot.id}/retry")

    assert response.status_code == 500
    assert "RAZORPAY_KEY_ID must be configured" in response.json()["detail"]


def test_payment_failure_changes_purchase_session_state_to_payment_failed(
    client_session,
    monkeypatch,
):
    client, session = client_session
    snapshot = make_purchase_snapshot(session, "purchase-payment-failure")
    order = make_failed_order(
        session,
        snapshot.id,
        status="CREATED",
        razorpay_order_id="order_failure_api",
        idempotency_key="idem_failure_api",
    )

    razorpay_client = Mock()
    razorpay_client.order.payments.return_value = {
        "items": [
            {
                "id": "pay_failure_api",
                "status": "failed",
                "amount": order.amount_paise,
                "method": "card",
                "error_reason": "payment_failed",
                "error_description": "Payment declined",
            }
        ]
    }
    monkeypatch.setattr(
        "apps.api.main.get_razorpay_client",
        lambda: razorpay_client,
    )

    response = client.post(
        "/test/razorpay/failure",
        json={
            "razorpay_payment_id": "pay_failure_api",
            "razorpay_order_id": "order_failure_api",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PAYMENT_FAILED"

    session.refresh(snapshot)
    session.refresh(order)

    assert snapshot.status == "PAYMENT_FAILED"
    assert order.status == "PAYMENT_FAILED"

    payment = session.exec(
        select(Payment).where(Payment.razorpay_payment_id == "pay_failure_api")
    ).one()
    assert payment.status == "FAILED"


@pytest.fixture
def client_session(session):
    app.dependency_overrides[get_session] = override_get_session(session)
    client = TestClient(app)
    try:
        yield client, session
    finally:
        app.dependency_overrides.clear()
