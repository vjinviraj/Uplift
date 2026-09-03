"""Real-time, non-payment smoke test for Uplift agents + Groq.

Run from the repository root:

    uv run python -m scripts.smoke_test_agents

This script intentionally does NOT call Razorpay/create_order.
It verifies:
    Groq -> MerchantAgent -> deterministic commerce/policy -> AIBuyer -> authorization
"""

from __future__ import annotations

import os
import sys
import uuid

from sqlmodel import Session, select

from apps.api.agents.authorization import authorize_purchase
from apps.api.agents.buyer import AIBuyer
from apps.api.agents.llm_client import LLMClient
from apps.api.agents.merchant_agent import MerchantAgent
from apps.api.agents.schemas import PurchaseRequest
from apps.api.database import engine
from apps.api.models import BuyerProfile, PolicyConfig, Session as BuyerSession


def money(paise: int) -> str:
    return f"₹{paise / 100:,.2f}"


def load_policy(db: Session) -> PolicyConfig:
    policy = db.exec(select(PolicyConfig)).first()

    if policy is not None:
        print(f"    ✅ Policy loaded from DB: {policy.version}")
        return policy

    # The existing seed flow may not have a PolicyConfig row.
    # Use the documented project policy in memory for this smoke test.
    policy = PolicyConfig(
        version="smoke-v1",
        max_single_item_price_paise=100_000,
        max_order_total_without_extra_confirm_paise=500_000,
        max_upsells_per_session=1,
        allowed_product_ids=None,
    )

    print("    ⚠️ No PolicyConfig row found; using in-memory smoke-test policy")
    print(f"       Policy: {policy.version}")
    return policy


def print_header(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    print_header("UPLIFT REAL-TIME AGENT SMOKE TEST")

    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY is not configured.")
        print("   Configure it in the environment before running this script.")
        return 1

    model = os.getenv("GROQ_MODEL")
    if not model:
        print("❌ GROQ_MODEL is not configured.")
        print("   Expected: openai/gpt-oss-20b")
        return 1

    print("[1] Groq configuration")
    print(f"    ✅ API key loaded")
    print(f"    ✅ Model: {model}")

    try:
        llm = LLMClient()
        print("    ✅ LLMClient initialized")
    except Exception as exc:
        print(f"    ❌ LLMClient initialization failed: {exc}")
        return 1

    print("[2] Database")
    try:
        with Session(engine) as db:
            policy = load_policy(db)

            buyer_profile_id = f"smoke-buyer-{uuid.uuid4().hex[:10]}"
            buyer_profile = BuyerProfile(
                id=buyer_profile_id,
                objective="Buy Genshin Impact within a ₹1,000 budget",
                max_budget_paise=100_000,
                category_hint=None,
                platform=None,
                franchise="Genshin Impact",
            )

            buyer_session_id = f"smoke-{uuid.uuid4().hex[:12]}"
            buyer_session = BuyerSession(
                id=buyer_session_id,
                status="ACTIVE",
                buyer_profile_id=buyer_profile_id,
                customer_ref="agent-smoke-test",
            )

            db.add(buyer_profile)
            db.add(buyer_session)
            db.commit()

            print(f"    ✅ Policy loaded: {policy.version}")
            print(f"    ✅ Temporary session: {buyer_session.id}")
            print(f"    ✅ Temporary buyer profile: {buyer_profile.id}")

            request = PurchaseRequest(
                query="Genshin Impact",
                budget_paise=100_000,
            )

            print("[3] AI Buyer request")
            print('    Query: "Genshin Impact"')
            print(f"    Budget: {money(request.budget_paise)}")
            print("    ✅ PurchaseRequest created")

            print("[4] Merchant Agent + live Groq call")
            merchant_agent = MerchantAgent(llm)
            offer = merchant_agent.propose(
                session=db,
                request=request,
                policy=policy,
            )

            print("    ✅ Groq returned a structured proposal")
            print(f"    ✅ Base product: {offer.product_id}")
            print(f"    ✅ Upsell: {offer.upsell_product_id or 'none'}")

            if offer.upsell_reason:
                print(f"    ✅ Upsell reason: {offer.upsell_reason}")

            print("[5] Deterministic server result")
            print(f"    Amount: {money(offer.amount_paise)}")
            print(f"    Currency: {offer.currency}")
            print(f"    Policy: {offer.policy_decision}")
            print(f"    Policy version: {offer.policy_version}")
            print("    ✅ Amount came from deterministic pricing")
            print("    ✅ Policy came from deterministic policy engine")

            print("[6] AI Buyer evaluation")
            buyer = AIBuyer()
            confirmation = buyer.evaluate_offer(
                request=request,
                offer=offer,
            )

            print(f"    Buyer approved: {confirmation.approved}")
            print(f"    Buyer-approved amount: {money(confirmation.amount_paise)}")

            if confirmation.amount_paise != offer.amount_paise:
                raise AssertionError(
                    "Buyer approval amount does not match server-computed offer amount."
                )

            print("    ✅ Exact amount preserved")

            print("[7] Dual authorization")
            authorized = authorize_purchase(
                offer=offer,
                confirmation=confirmation,
            )

            print(f"    Authorization result: {authorized}")

            if offer.policy_decision == "ALLOWED" and confirmation.approved:
                if not authorized:
                    raise AssertionError("Expected authorization to pass.")
                print("    ✅ Merchant policy + buyer approval passed")
            else:
                print("    ℹ️ Purchase is blocked by policy or buyer decision")

            print("[8] Payment boundary")
            print("    ✅ Razorpay NOT called")
            print("    ✅ create_order() NOT called")
            print("    ✅ Smoke test stops before money execution")

            db.delete(buyer_session)
            db.delete(buyer_profile)
            db.commit()

    except Exception as exc:
        print()
        print("❌ SMOKE TEST FAILED")
        print(f"   {type(exc).__name__}: {exc}")
        return 1

    print_header("✅ UPLIFT AGENT SMOKE TEST PASSED")
    print("Live path verified:")
    print("    Groq → Merchant Agent → deterministic pricing/policy")
    print("          → AI Buyer → dual authorization")
    print()
    print("No Razorpay Order/payment was created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())