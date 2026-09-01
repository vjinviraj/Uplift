import hashlib
import hmac

import pytest

from apps.api.razorpay_client.verification import verify_payment_signature


def generate_test_signature(
    order_id: str,
    payment_id: str,
    secret: str,
) -> str:
    message = f"{order_id}|{payment_id}"

    return hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def test_valid_signature_is_accepted():
    order_id = "order_test_001"
    payment_id = "pay_test_001"
    secret = "test_secret"

    signature = generate_test_signature(
        order_id,
        payment_id,
        secret,
    )

    assert verify_payment_signature(
        order_id=order_id,
        payment_id=payment_id,
        signature=signature,
        secret=secret,
    ) is True


def test_tampered_signature_is_rejected():
    with pytest.raises(ValueError, match="Invalid payment signature"):
        verify_payment_signature(
            order_id="order_test_001",
            payment_id="pay_test_001",
            signature="tampered",
            secret="test_secret",
        )


def test_missing_signature_is_rejected():
    with pytest.raises(ValueError, match="Payment signature is required"):
        verify_payment_signature(
            order_id="order_test_001",
            payment_id="pay_test_001",
            signature="",
            secret="test_secret",
        )