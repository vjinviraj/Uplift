from sqlmodel import Session, select

from apps.api.razorpay_client.orders import create_razorpay_order
from apps.api.models import Order, Payment
from apps.api.audit.service import record_audit_event


def create_order(
    session: Session,
    razorpay_client,
    session_id: str,
    amount_paise: int,
    idempotency_key: str,
) -> Order:
    existing_order = session.exec(
        select(Order).where(Order.idempotency_key == idempotency_key)
    ).first()

    if existing_order is not None:
        raise ValueError("Idempotency key already exists")

    razorpay_order = create_razorpay_order(
        client=razorpay_client,
        amount_paise=amount_paise,
        receipt=idempotency_key,
    )

    order = Order(
        session_id=session_id,
        amount_paise=amount_paise,
        currency="INR",
        status="CREATED",
        razorpay_order_id=razorpay_order["id"],
        idempotency_key=idempotency_key,
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    return order


MAX_PAYMENT_RETRIES = 1


def handle_payment_failure(
    *,
    retry_count: int,
    failure_reason: str,
) -> dict[str, str | int]:
    if retry_count < 0:
        raise ValueError("retry_count cannot be negative")

    if retry_count < MAX_PAYMENT_RETRIES:
        return {
            "status": "RETRY_AVAILABLE",
            "retry_count": retry_count + 1,
            "failure_reason": failure_reason,
        }

    return {
        "status": "RETRY_EXHAUSTED",
        "retry_count": retry_count,
        "failure_reason": failure_reason,
    }


def retry_order(
    *,
    session: Session,
    razorpay_client,
    failed_order: Order,
    retry_count: int,
    idempotency_key: str,
    agent_run_id: str = "system",
) -> Order:
    if retry_count >= MAX_PAYMENT_RETRIES:
        record_audit_event(
            session=session,
            agent_run_id=agent_run_id,
            session_id=failed_order.session_id,
            actor_type="SYSTEM",
            action_id="retry-exhausted",
            event_type="retry_exhausted",
            reason="Payment retry limit exhausted",
            razorpay_order_id=failed_order.razorpay_order_id,
        )

        raise ValueError("Payment retry limit exhausted")

    if failed_order.status != "PAYMENT_FAILED":
        raise ValueError("Only failed orders can be retried")

    retry = create_order(
        session=session,
        razorpay_client=razorpay_client,
        session_id=failed_order.session_id,
        amount_paise=failed_order.amount_paise,
        idempotency_key=idempotency_key,
    )

    record_audit_event(
        session=session,
        agent_run_id=agent_run_id,
        session_id=failed_order.session_id,
        actor_type="SYSTEM",
        action_id="retry-started",
        event_type="retry_started",
        razorpay_order_id=retry.razorpay_order_id,
        payload={
            "previous_order_id": failed_order.razorpay_order_id,
            "retry_order_id": retry.razorpay_order_id,
            "retry_count": retry_count + 1,
        },
    )

    return retry


def record_payment_failure(
    *,
    session: Session,
    order: Order,
    razorpay_payment_id: str,
    method: str,
    failure_reason: str,
    agent_run_id: str = "system",
) -> Payment:
    if not razorpay_payment_id:
        raise ValueError("razorpay_payment_id is required")

    if not method:
        raise ValueError("method is required")

    if not failure_reason:
        raise ValueError("failure_reason is required")

    order.status = "PAYMENT_FAILED"

    payment = Payment(
        order_id=order.id,
        razorpay_payment_id=razorpay_payment_id,
        status="FAILED",
        method=method,
        failure_reason=failure_reason,
    )

    session.add(order)
    session.add(payment)
    session.commit()
    session.refresh(payment)

    record_audit_event(
        session=session,
        agent_run_id=agent_run_id,
        session_id=order.session_id,
        actor_type="SYSTEM",
        action_id="payment-failure",
        event_type="payment_failed",
        reason=failure_reason,
        razorpay_order_id=order.razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
    )

    return payment