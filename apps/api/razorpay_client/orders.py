from typing import Any

import razorpay


def create_razorpay_order(
    client: razorpay.Client,
    amount_paise: int,
    receipt: str,
) -> dict[str, Any]:
    if amount_paise <= 0:
        raise ValueError("amount_paise must be greater than 0")

    return client.order.create(
        data={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
        }
    )