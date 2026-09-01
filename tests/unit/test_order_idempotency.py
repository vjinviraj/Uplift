import pytest
from sqlmodel import Session, create_engine, select
from sqlmodel.pool import StaticPool

from apps.api.models import Order
from apps.api.razorpay_client.service import create_order


def test_duplicate_idempotency_key_is_rejected():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Order.metadata.create_all(engine)

    fake_client = type(
        "FakeClient",
        (),
        {
            "order": type(
                "FakeOrder",
                (),
                {
                    "create": lambda self, data: {
                        "id": "order_test_001",
                        "amount": data["amount"],
                        "currency": data["currency"],
                        "receipt": data["receipt"],
                        "status": "created",
                    }
                },
            )()
        },
    )()

    with Session(engine) as session:
        create_order(
            session=session,
            razorpay_client=fake_client,
            session_id="session-001",
            amount_paise=249800,
            idempotency_key="idem-001",
        )

        with pytest.raises(ValueError, match="Idempotency key already exists"):
            create_order(
                session=session,
                razorpay_client=fake_client,
                session_id="session-001",
                amount_paise=249800,
                idempotency_key="idem-001",
            )


def test_different_idempotency_keys_create_different_orders():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Order.metadata.create_all(engine)

    fake_client = type(
        "FakeClient",
        (),
        {
            "order": type(
                "FakeOrder",
                (),
                {
                    "create": lambda self, data: {
                        "id": f"order_{data['receipt']}",
                        "amount": data["amount"],
                        "currency": data["currency"],
                        "receipt": data["receipt"],
                        "status": "created",
                    }
                },
            )()
        },
    )()

    with Session(engine) as session:
        first = create_order(
            session=session,
            razorpay_client=fake_client,
            session_id="session-001",
            amount_paise=249800,
            idempotency_key="idem-001",
        )

        second = create_order(
            session=session,
            razorpay_client=fake_client,
            session_id="session-001",
            amount_paise=249800,
            idempotency_key="idem-002",
        )

        orders = session.exec(select(Order)).all()

    assert first.id != second.id
    assert len(orders) == 2