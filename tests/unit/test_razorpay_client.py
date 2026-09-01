import pytest

from apps.api.razorpay_client.client import get_razorpay_client


def test_razorpay_client_requires_credentials(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    with pytest.raises(
        RuntimeError,
        match="RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured",
    ):
        get_razorpay_client()


def test_razorpay_client_initializes_with_credentials(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_dummy")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "dummy_secret")

    client = get_razorpay_client()

    assert client is not None