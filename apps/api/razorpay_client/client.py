import razorpay

from apps.api.config import get_setting


def get_razorpay_client() -> razorpay.Client:
    key_id = get_setting("RAZORPAY_KEY_ID")
    key_secret = get_setting("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise RuntimeError(
            "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured."
        )

    return razorpay.Client(auth=(key_id, key_secret))
