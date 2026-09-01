from unittest.mock import Mock

from apps.api.razorpay_client.orders import create_razorpay_order


def test_create_razorpay_order_sends_integer_amount():
    client = Mock()
    client.order.create.return_value = {
        "id": "order_test_001",
        "amount": 249800,
        "currency": "INR",
        "receipt": "uplift-order-001",
        "status": "created",
    }

    result = create_razorpay_order(
        client=client,
        amount_paise=249800,
        receipt="uplift-order-001",
    )

    client.order.create.assert_called_once_with(
        data={
            "amount": 249800,
            "currency": "INR",
            "receipt": "uplift-order-001",
        }
    )

    assert result["id"] == "order_test_001"
    assert result["amount"] == 249800
    assert result["status"] == "created"


def test_create_razorpay_order_rejects_non_positive_amount():
    client = Mock()

    try:
        create_razorpay_order(
            client=client,
            amount_paise=0,
            receipt="uplift-order-001",
        )
    except ValueError as exc:
        assert str(exc) == "amount_paise must be greater than 0"
    else:
        raise AssertionError("Expected ValueError")