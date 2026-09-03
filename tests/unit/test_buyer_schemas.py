import pytest
from pydantic import ValidationError

from apps.api.agents.schemas import PurchaseConfirmation


def test_purchase_confirmation_accepts_approved_confirmation():
    confirmation = PurchaseConfirmation(
        approved=True,
        amount_paise=89900,
    )

    assert confirmation.approved is True
    assert confirmation.amount_paise == 89900


def test_purchase_confirmation_accepts_rejection():
    confirmation = PurchaseConfirmation(
        approved=False,
        amount_paise=89900,
    )

    assert confirmation.approved is False
    assert confirmation.amount_paise == 89900


def test_purchase_confirmation_rejects_negative_amount():
    with pytest.raises(ValidationError):
        PurchaseConfirmation(
            approved=True,
            amount_paise=-1,
        )


def test_purchase_confirmation_requires_amount():
    with pytest.raises(ValidationError):
        PurchaseConfirmation(
            approved=True,
        )


def test_purchase_confirmation_requires_approved():
    with pytest.raises(ValidationError):
        PurchaseConfirmation(
            amount_paise=89900,
        )