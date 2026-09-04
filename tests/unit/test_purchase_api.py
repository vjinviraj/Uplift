from unittest.mock import Mock

from fastapi.testclient import TestClient

from apps.api.agents.schemas import PurchaseOffer
from apps.api.main import app


class StubWorkflow:
    def __init__(self, offer: PurchaseOffer):
        self.offer = offer
        self.confirmation = Mock(approved=True, amount_paise=offer.amount_paise)

    def prepare_offer(self, *, session, request, policy):
        return self.offer

    def evaluate_offer(self, *, request, offer):
        return self.confirmation


def make_offer(amount_paise: int = 89_900) -> PurchaseOffer:
    return PurchaseOffer(
        product_id="GAME-001",
        upsell_product_id="MER-002",
        upsell_reason="Relevant low-cost merchandise item.",
        amount_paise=amount_paise,
        currency="INR",
        breakdown=[
            {
                "product_id": "GAME-001",
                "name": "Genshin Impact - Digital Edition",
                "qty": 1,
                "unit_price_paise": 0,
                "line_total_paise": 0,
            },
            {
                "product_id": "MER-002",
                "name": "Genshin Impact Vision Keychain - Pyro Edition",
                "qty": 1,
                "unit_price_paise": amount_paise,
                "line_total_paise": amount_paise,
            },
        ],
        policy_decision="ALLOWED",
        policy_reason="Within merchant and buyer limits.",
        policy_version="v1",
    )


def test_prepare_purchase_persists_exact_offer(monkeypatch):
    offer = make_offer()
    monkeypatch.setattr("apps.api.main.build_workflow", lambda: StubWorkflow(offer))

    with TestClient(app) as client:
        response = client.post(
            "/api/purchases/prepare",
            json={"query": "Genshin Impact", "budget_paise": 250_000},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "AWAITING_APPROVAL"
        assert body["offer"]["amount_paise"] == 89_900

        session_id = body["session_id"]
        stored = client.get(f"/api/purchases/{session_id}")
        assert stored.status_code == 200
        assert stored.json()["offer"] == body["offer"]


def test_approve_purchase_requires_exact_server_amount(monkeypatch):
    offer = make_offer()
    monkeypatch.setattr("apps.api.main.build_workflow", lambda: StubWorkflow(offer))

    with TestClient(app) as client:
        prepare = client.post(
            "/api/purchases/prepare",
            json={"query": "Genshin Impact", "budget_paise": 250_000},
        )
        session_id = prepare.json()["session_id"]

        response = client.post(
            f"/api/purchases/{session_id}/approve",
            json={"approved": True, "amount_paise": 99_900},
        )

        assert response.status_code == 409
        assert "exactly match" in response.json()["detail"]


def test_reject_purchase_never_calls_payment(monkeypatch):
    offer = make_offer()
    workflow = StubWorkflow(offer)
    monkeypatch.setattr("apps.api.main.build_workflow", lambda: workflow)
    create_order = Mock()
    monkeypatch.setattr("apps.api.main.get_razorpay_client", create_order)

    with TestClient(app) as client:
        prepare = client.post(
            "/api/purchases/prepare",
            json={"query": "Genshin Impact", "budget_paise": 250_000},
        )
        session_id = prepare.json()["session_id"]

        response = client.post(
            f"/api/purchases/{session_id}/approve",
            json={"approved": False, "amount_paise": 89_900},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"
        create_order.assert_not_called()
