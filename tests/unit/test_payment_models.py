from datetime import datetime

from apps.api.models import Order, Payment


def test_order_model_has_required_fields():
    order = Order(
        session_id="session-001",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_test_001",
        idempotency_key="idem-001",
    )

    assert order.session_id == "session-001"
    assert order.amount_paise == 249800
    assert order.currency == "INR"
    assert order.status == "CREATED"
    assert order.razorpay_order_id == "order_test_001"
    assert order.idempotency_key == "idem-001"
    assert isinstance(order.created_at, datetime)


def test_payment_model_has_required_fields():
    payment = Payment(
        order_id=1,
        razorpay_payment_id="pay_test_001",
        status="CAPTURED",
        method="upi",
    )

    assert payment.order_id == 1
    assert payment.razorpay_payment_id == "pay_test_001"
    assert payment.status == "CAPTURED"
    assert payment.method == "upi"
    assert payment.verified_at is None
    assert payment.failure_reason is None