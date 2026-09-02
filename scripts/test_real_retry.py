from apps.api.database import get_session
from apps.api.models import Order
from apps.api.razorpay_client.client import get_razorpay_client
from apps.api.razorpay_client.service import retry_order
from sqlmodel import select


failed_razorpay_order_id = "order_TXFb1SConY4LIe"


with next(get_session()) as session:
    failed_order = session.exec(
        select(Order).where(
            Order.razorpay_order_id == failed_razorpay_order_id
        )
    ).first()

    if failed_order is None:
        raise RuntimeError("Failed local order not found.")

    print("Failed local order:", failed_order.id)
    print("Status:", failed_order.status)
    print("Amount:", failed_order.amount_paise)

    retry = retry_order(
        session=session,
        razorpay_client=get_razorpay_client(),
        failed_order=failed_order,
        retry_count=0,
        idempotency_key="real-retry-order-003",
    )

    print("Retry local order:", retry.id)
    print("Retry Razorpay order:", retry.razorpay_order_id)
    print("Retry amount:", retry.amount_paise)