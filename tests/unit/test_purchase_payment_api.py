from datetime import datetime, timezone
import os

from apps.api.models import Order, Payment, PurchaseSessionState
from apps.api.razorpay_client import reconciliation


def test_purchase_payment_verify_reconciles_paid_payment(client, session, monkeypatch):
    snapshot = PurchaseSessionState(
        id="purchase-test-verify",
        request_json='{"query":"Genshin Impact","budget_paise":250000,"category_hint":"Games","platform_hint":null,"franchise_hint":"Genshin Impact"}',
        offer_json='{"product_id":"GAME-001","upsell_product_id":null,"upsell_reason":null,"amount_paise":89900,"currency":"INR","breakdown":[],"policy_decision":"ALLOWED","policy_reason":"Allowed","policy_version":"test"}',
        status="ORDER_CREATED",
    )
    order = Order(
        session_id=snapshot.id,
        amount_paise=89900,
        currency="INR",
        status="CREATED",
        razorpay_order_id="order_TEST123",
        idempotency_key="uplift-purchase-test-verify",
        created_at=datetime.now(timezone.utc),
    )
    session.add(snapshot)
    session.add(order)
    session.commit()
    session.refresh(order)

    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "test-secret")

    calls = []

    def fake_verify(*, order_id, payment_id, signature, secret):
        calls.append((order_id, payment_id, signature, secret))

    def fake_client():
        class FakeOrder:
            def payments(self, razorpay_order_id):
                return {
                    "items": [
                        {
                            "id": "pay_TEST123",
                            "status": "captured",
                            "amount": 89900,
                        }
                    ]
                }

        class FakeClient:
            order = FakeOrder()

        return FakeClient()

    monkeypatch.setattr("apps.api.main.verify_payment_signature", fake_verify)
    monkeypatch.setattr("apps.api.main.get_razorpay_client", fake_client)

    response = client.post(
        f"/api/purchases/{snapshot.id}/verify",
        json={
            "razorpay_payment_id": "pay_TEST123",
            "razorpay_order_id": "order_TEST123",
            "razorpay_signature": "signature",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PAID"
    assert calls == [("order_TEST123", "pay_TEST123", "signature", "test-secret")]

    session.expire_all()
    refreshed_order = session.get(Order, order.id)
    refreshed_snapshot = session.get(PurchaseSessionState, snapshot.id)
    payment = session.exec(
        __import__("sqlmodel").select(Payment).where(Payment.order_id == order.id)
    ).first()

    assert refreshed_order.status == "PAID"
    assert refreshed_snapshot.status == "PAID"
    assert payment is not None
    assert payment.status == "SUCCESS"


def test_purchase_payment_verify_rejects_order_from_another_session(client, session, monkeypatch):
    snapshot = PurchaseSessionState(
        id="purchase-session-owned",
        request_json='{"query":"Genshin Impact","budget_paise":250000,"category_hint":"Games","platform_hint":null,"franchise_hint":"Genshin Impact"}',
        offer_json='{"product_id":"GAME-001","upsell_product_id":null,"upsell_reason":null,"amount_paise":89900,"currency":"INR","breakdown":[],"policy_decision":"ALLOWED","policy_reason":"Allowed","policy_version":"test"}',
        status="ORDER_CREATED",
    )
    order = Order(
        session_id="purchase-other-session",
        amount_paise=89900,
        status="CREATED",
        razorpay_order_id="order_OTHER",
        idempotency_key="uplift-other",
    )
    session.add(snapshot)
    session.add(order)
    session.commit()

    response = client.post(
        f"/api/purchases/{snapshot.id}/verify",
        json={
            "razorpay_payment_id": "pay_OTHER",
            "razorpay_order_id": "order_OTHER",
            "razorpay_signature": "signature",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Razorpay order not found for purchase session"
