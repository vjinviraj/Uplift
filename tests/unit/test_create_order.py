from sqlmodel import Session, create_engine, select
from sqlmodel.pool import StaticPool

from apps.api.models import Order
from apps.api.razorpay_client.service import create_order


def test_create_order_persists_razorpay_order():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Order.metadata.create_all(engine)

    razorpay_client = type(
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
        order = create_order(
            session=session,
            razorpay_client=razorpay_client,
            session_id="session-001",
            amount_paise=249800,
            idempotency_key="idem-001",
        )

        saved = session.exec(
            select(Order).where(Order.id == order.id)
        ).one()

    assert saved.razorpay_order_id == "order_test_001"
    assert saved.amount_paise == 249800
    assert saved.currency == "INR"
    assert saved.status == "CREATED"
    assert saved.idempotency_key == "idem-001"