from datetime import datetime, timezone

from sqlmodel import Session, select

from apps.api.models import Order, Payment


def reconcile_payment(
    *,
    session: Session,
    razorpay_client,
    order: Order,
    expected_amount_paise: int,
) -> dict[str, str]:
    result = razorpay_client.order.payments(order.razorpay_order_id)

    payments = result.get("items", [])
    captured_payment_found = False

    for payment_data in payments:
        if payment_data.get("status") != "captured":
            continue

        captured_payment_found = True

        if payment_data.get("amount") != expected_amount_paise:
            continue

        payment = session.exec(
            select(Payment).where(
                Payment.order_id == order.id,
                Payment.razorpay_payment_id == payment_data["id"],
            )
        ).first()

        if payment is None:
            raise ValueError("Local payment record not found")

        payment.status = "SUCCESS"
        payment.verified_at = datetime.now(timezone.utc)

        order.status = "PAID"

        session.add(payment)
        session.add(order)
        session.commit()

        return {
            "status": "PAID",
            "razorpay_payment_id": payment_data["id"],
        }

    if captured_payment_found:
        raise ValueError("Payment amount mismatch")

    return {
        "status": "NOT_PAID",
    }