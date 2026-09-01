import hashlib
import hmac


def verify_payment_signature(
    order_id: str,
    payment_id: str,
    signature: str,
    secret: str,
) -> bool:
    if not signature:
        raise ValueError("Payment signature is required")

    message = f"{order_id}|{payment_id}"

    expected_signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise ValueError("Invalid payment signature")

    return True