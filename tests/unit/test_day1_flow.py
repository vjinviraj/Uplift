from sqlmodel import Session

from apps.api.audit.service import record_audit_event
from apps.api.commerce.catalog import (
    get_upsell_candidates,
    price_order,
    search_catalog,
)
from apps.api.database import engine
from apps.api.models import PolicyConfig
from apps.api.policy.engine import check_policy


def test_day1_catalog_to_policy_to_audit():
    with Session(engine) as session:
        search_result = search_catalog(
            session=session,
            query="Genshin Impact",
            category_hint="Games",
        )

        assert search_result["matches"]

        product = search_result["matches"][0]

        assert product["product_id"] == "GAME-001"

        candidate_result = get_upsell_candidates(
            session=session,
            product_id=product["product_id"],
        )

        assert candidate_result["candidates"]

        upsell = next(
            (
                candidate
                for candidate in candidate_result["candidates"]
                if candidate["max_autonomous"]
            ),
            None,
        )

        assert upsell is not None
        assert upsell["product_id"] == "MER-002"
        assert upsell["price_paise"] == 89_900
        assert upsell["max_autonomous"] is True

        policy = PolicyConfig(
            version="v1",
            max_single_item_price_paise=100_000,
            max_order_total_without_extra_confirm_paise=500_000,
            max_upsells_per_session=1,
            allowed_product_ids=None,
        )

        price_result = price_order(
            session=session,
            line_items=[
                {
                    "product_id": product["product_id"],
                    "qty": 1,
                },
                {
                    "product_id": upsell["product_id"],
                    "qty": 1,
                },
            ],
        )

        total_paise = price_result["amount_paise"]

        result = check_policy(
            policy=policy,
            total_paise=total_paise,
            buyer_budget_paise=250_000,
            upsell_count=1,
            upsell_price_paise=upsell["price_paise"],
            product_ids=[
                product["product_id"],
                upsell["product_id"],
            ],
        )

        event = record_audit_event(
            session=session,
            agent_run_id="day1-run-002",
            session_id="day1-session-002",
            actor_type="policy_engine",
            action_id="policy-check-002",
            event_type="policy_checked",
            decision=result.decision,
            reason=result.reason,
            policy_version=result.policy_version,
            payload={
                "product_id": product["product_id"],
                "upsell_product_id": upsell["product_id"],
                "total_paise": total_paise,
            },
        )

        assert total_paise == 89_900
        assert price_result["currency"] == "INR"

        assert result.decision == "ALLOWED"
        assert event.decision == "ALLOWED"
        assert event.policy_version == "v1"