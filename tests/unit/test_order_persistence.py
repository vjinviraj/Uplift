from sqlmodel import Session, create_engine, select
from sqlmodel.pool import StaticPool

from apps.api.models import Order


def test_order_can_be_persisted():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Order.metadata.create_all(engine)

    order = Order(
        session_id="session-001",
        amount_paise=249800,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_test_001",
        idempotency_key="idem-001",
    )

    with Session(engine) as session:
        session.add(order)
        session.commit()
        session.refresh(order)

        saved = session.exec(
            select(Order).where(Order.id == order.id)
        ).one()

    assert saved.id is not None
    assert saved.session_id == "session-001"
    assert saved.amount_paise == 249800
    assert saved.razorpay_order_id == "order_test_001"
    assert saved.idempotency_key == "idem-001"
    assert saved.status == "CREATED"