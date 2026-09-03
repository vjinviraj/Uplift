"""Real-time payment smoke test for Uplift agents + Groq + Razorpay.

Run from the repository root:

    uv run python -m scripts.smoke_test_payment

This script tests the complete payment flow including:
    Groq -> MerchantAgent -> deterministic commerce/policy -> AIBuyer 
    -> authorization -> Razorpay Order -> Checkout -> verification
"""

from __future__ import annotations

import os
import sys
import uuid
import webbrowser
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

from apps.api.agents.authorization import authorize_purchase
from apps.api.agents.buyer import AIBuyer
from apps.api.agents.llm_client import LLMClient
from apps.api.agents.merchant_agent import MerchantAgent
from apps.api.agents.schemas import PurchaseRequest
from apps.api.database import engine
from apps.api.models import BuyerProfile, PolicyConfig, Session as BuyerSession
from apps.api.razorpay_client.client import get_razorpay_client
from apps.api.razorpay_client.service import create_order


def money(paise: int) -> str:
    return f"₹{paise / 100:,.2f}"


def load_policy(db: Session) -> PolicyConfig:
    policy = db.exec(select(PolicyConfig)).first()

    if policy is not None:
        print(f"    ✅ Policy loaded from DB: {policy.version}")
        return policy

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


def create_checkout_html(
    razorpay_key_id: str,
    order_id: str,
    amount_paise: int,
    currency: str,
    local_order_id: int,
    checkout_success_url: str = "http://localhost:8000/test/razorpay/verify",
) -> Path:
    """Create a temporary HTML file for Razorpay Standard Checkout."""
    
    # Amount in paise to rupees
    amount_rupees = amount_paise / 100
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Uplift - Payment Checkout</title>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .card {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #1a1a1a;
            margin: 0;
        }}
        .header p {{
            color: #666;
            margin: 5px 0 0;
        }}
        .info {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }}
        .info-row:last-child {{
            border-bottom: none;
        }}
        .label {{
            color: #666;
        }}
        .value {{
            font-weight: 600;
            color: #1a1a1a;
        }}
        .button {{
            width: 100%;
            padding: 15px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }}
        .button:hover {{
            background: #45a049;
        }}
        .test-mode {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            color: #856404;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }}
        .status {{
            margin-top: 20px;
            padding: 12px;
            border-radius: 8px;
            display: none;
        }}
        .status.success {{
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }}
        .status.error {{
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }}
        .status.visible {{
            display: block;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>Uplift</h1>
            <p>AI-Powered Gaming Marketplace</p>
        </div>

        <div class="test-mode">
            🔧 <strong>TEST MODE</strong><br>
            No real money will be deducted. Use Razorpay test cards.
        </div>

        <div class="info">
            <div class="info-row">
                <span class="label">Order ID</span>
                <span class="value">{local_order_id}</span>
            </div>
            <div class="info-row">
                <span class="label">Amount</span>
                <span class="value">{money(amount_paise)}</span>
            </div>
            <div class="info-row">
                <span class="label">Currency</span>
                <span class="value">{currency}</span>
            </div>
            <div class="info-row">
                <span class="label">Razorpay Order</span>
                <span class="value" style="font-size: 12px;">{order_id}</span>
            </div>
        </div>

        <button class="button" id="payButton">Pay {money(amount_paise)}</button>

        <div id="status" class="status"></div>
    </div>

    <script>
        const successUrl = '{checkout_success_url}';
        const razorpayKeyId = '{razorpay_key_id}';
        const razorpayOrderId = '{order_id}';
        const amount = {amount_rupees};
        const currency = '{currency}';

        document.getElementById('payButton').addEventListener('click', function() {{
            const options = {{
                key: razorpayKeyId,
                amount: amount * 100,
                currency: currency,
                name: 'Uplift',
                description: 'AI-Powered Gaming Marketplace Purchase',
                order_id: razorpayOrderId,
                prefill: {{
                    name: 'Smoke Test User',
                    email: 'smoke-test@uplift.ai',
                    contact: '9999999999'
                }},
                theme: {{
                    color: '#4CAF50'
                }},
                modal: {{
                    ondismiss: function() {{
                        showStatus('Payment cancelled by user.', 'error');
                    }}
                }},
                handler: function(response) {{
                    // Send payment details to server for verification
                    fetch(successUrl, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_signature: response.razorpay_signature
                        }})
                    }})
                    .then(res => res.json())
                    .then(data => {{
                        if (data.status === 'PAID') {{
                            showStatus('✅ Payment successful! Signature verified.', 'success');
                            document.getElementById('payButton').disabled = true;
                            document.getElementById('payButton').textContent = 'Payment Complete';
                        }} else {{
                            showStatus('❌ Payment verification failed: ' + data.message, 'error');
                        }}
                    }})
                    .catch(error => {{
                        showStatus('❌ Error verifying payment: ' + error.message, 'error');
                    }});
                }}
            }};

            const rzp = new Razorpay(options);
            rzp.open();
        }});

        function showStatus(message, type) {{
            const statusEl = document.getElementById('status');
            statusEl.textContent = message;
            statusEl.className = 'status visible ' + type;
        }}
    </script>
</body>
</html>"""
    
    # Write to temporary file
    temp_dir = Path("/tmp") if sys.platform != "win32" else Path(os.environ.get("TEMP", "."))
    html_path = temp_dir / f"razorpay_checkout_{uuid.uuid4().hex[:8]}.html"
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return html_path


def main() -> int:
    print_header("UPLIFT REAL-TIME PAYMENT SMOKE TEST")

    # Check Groq configuration
    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY is not configured.")
        print("   Configure it in the environment before running this script.")
        return 1

    model = os.getenv("GROQ_MODEL")
    if not model:
        print("❌ GROQ_MODEL is not configured.")
        print("   Expected: openai/gpt-oss-20b")
        return 1

    # Check Razorpay configuration
    razorpay_key_id = os.getenv("RAZORPAY_KEY_ID")
    razorpay_key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    
    if not razorpay_key_id or not razorpay_key_secret:
        print("❌ Razorpay credentials not configured.")
        print("   Required: RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET")
        return 1

    print("[1] Configuration")
    print(f"    ✅ Groq API key loaded")
    print(f"    ✅ Groq Model: {model}")
    print(f"    ✅ Razorpay Key ID: {razorpay_key_id[:8]}...")
    print(f"    ✅ Razorpay Key Secret: {'*' * 8}")

    # Initialize components
    try:
        llm = LLMClient()
        razorpay_client = get_razorpay_client()
        print("    ✅ LLMClient initialized")
        print("    ✅ Razorpay client initialized")
    except Exception as exc:
        print(f"    ❌ Initialization failed: {exc}")
        return 1

    print("[2] Database")
    try:
        with Session(engine) as db:
            policy = load_policy(db)

            buyer_profile_id = f"payment-smoke-buyer-{uuid.uuid4().hex[:10]}"
            buyer_profile = BuyerProfile(
                id=buyer_profile_id,
                objective="Looking for a small Genshin Impact accessory as a gift, budget under ₹5,000",
                max_budget_paise=500_000,
                category_hint=None,
                platform=None,
                franchise="Genshin Impact",
            )

            buyer_session_id = f"payment-smoke-{uuid.uuid4().hex[:12]}"
            buyer_session = BuyerSession(
                id=buyer_session_id,
                status="ACTIVE",
                buyer_profile_id=buyer_profile_id,
                customer_ref="payment-smoke-test",
            )

            db.add(buyer_profile)
            db.add(buyer_session)
            db.commit()

            print(f"    ✅ Policy loaded: {policy.version}")
            print(f"    ✅ Temporary session: {buyer_session.id}")
            print(f"    ✅ Temporary buyer profile: {buyer_profile.id}")

            request = PurchaseRequest(
                query="I'm looking for a small Genshin Impact accessory as a gift, and I'd like to keep the total under ₹5,000.",
                budget_paise=500_000,
            )

            print("[3] AI Buyer request")
            print('    Query: "I\'m looking for a small Genshin Impact accessory as a gift, and I\'d like to keep the total under ₹5,000."')
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
            print(f"    ✅ Amount: {money(offer.amount_paise)}")

            if offer.upsell_reason:
                print(f"    ✅ Upsell reason: {offer.upsell_reason}")

            # Smoke test guard: ensure offer doesn't exceed budget
            if offer.amount_paise > request.budget_paise:
                raise RuntimeError(
                    f"Smoke-test offer exceeds buyer budget: "
                    f"{money(offer.amount_paise)} > {money(request.budget_paise)}"
                )

            print("[5] AI Buyer evaluation")
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

            print("[6] Dual authorization")
            authorized = authorize_purchase(
                offer=offer,
                confirmation=confirmation,
            )

            print(f"    Authorization result: {authorized}")

            if offer.policy_decision != "ALLOWED":
                raise RuntimeError(
                    f"Purchase blocked by policy: {offer.policy_decision}\n"
                    f"This test requires a policy ALLOWED decision. "
                    f"Check your PolicyConfig and deterministic pricing logic."
                )

            if not confirmation.approved:
                raise RuntimeError(
                    f"Purchase rejected by AI Buyer.\n"
                    f"This test requires buyer approval. "
                    f"Try adjusting the budget or query."
                )

            if not authorized:
                raise RuntimeError(
                    f"Purchase failed dual authorization.\n"
                    f"Policy: {offer.policy_decision}, "
                    f"Buyer approved: {confirmation.approved}"
                )

            print("    ✅ Merchant policy + buyer approval passed")

            print("[7] Razorpay Order creation")
            try:
                local_order = create_order(
                    session=db,
                    razorpay_client=razorpay_client,
                    session_id=buyer_session.id,
                    amount_paise=offer.amount_paise,
                    idempotency_key=f"payment-smoke-{uuid.uuid4().hex}",
                )
                
                print(f"    ✅ Local Order created (ID: {local_order.id})")
                print(f"    ✅ Razorpay Order ID: {local_order.razorpay_order_id}")
                print(f"    ✅ Amount: {money(local_order.amount_paise)}")
                print(f"    ✅ Currency: {local_order.currency}")
                print(f"    ✅ Status: {local_order.status}")
                
                razorpay_order_id = local_order.razorpay_order_id
                local_order_id = local_order.id
                
            except Exception as exc:
                print(f"    ❌ Order creation failed: {exc}")
                return 1

            print("[8] Standard Checkout")
            print("    Opening Razorpay Checkout...")
            
            html_path = create_checkout_html(
                razorpay_key_id=razorpay_key_id,
                order_id=razorpay_order_id,
                amount_paise=offer.amount_paise,
                currency=offer.currency,
                local_order_id=local_order_id,
            )
            
            print(f"    ✅ Checkout HTML: {html_path}")
            print("    ⏳ Waiting for Test Mode payment...")
            print()
            print("    Use Razorpay test cards:")
            print("    - Card: 4242 4242 4242 4242")
            print("    - Expiry: any future date")
            print("    - CVV: any 3 digits")
            print("    - Success Flow: Simulate bank approval")
            print()
            
            # Open in browser
            webbrowser.open(f"file://{html_path}")
            
            print("    ✅ Checkout opened in your browser")
            print("    ⏳ Complete the payment flow in the browser...")
            print()
            print("    Press Ctrl+C if you need to cancel.")
            print()
            
            # Wait for user to complete payment
            input("    Press Enter after completing the payment flow...")
            
            # Check payment status
            print("[9] Payment verification")
            
            # The Checkout callback is handled by FastAPI in a separate DB session.
            # Expire this session's cached objects so we read the committed state.
            db.expire_all()
            
            # Query the latest payment for this order
            from apps.api.models import Order, Payment
            
            order = db.exec(select(Order).where(Order.id == local_order_id)).first()
            if not order:
                raise RuntimeError("Order not found in database")
            
            # Refresh the order to get the latest committed state
            db.refresh(order)
            
            print(f"    Local Order status: {order.status}")
            
            # Hard failure if order is not PAID
            if order.status != "PAID":
                raise RuntimeError(
                    f"Payment verification did not complete. "
                    f"Local Order status is {order.status}, expected PAID."
                )
            
            print("    ✅ Order marked as PAID")
            
            # Check for successful payment
            payments = db.exec(
                select(Payment).where(Payment.order_id == local_order_id)
            ).all()
            
            successful_payment = next(
                (payment for payment in payments if payment.status == "SUCCESS"),
                None,
            )
            
            if successful_payment is None:
                raise RuntimeError(
                    "No successful Payment record found after Checkout."
                )
            
            print(
                f"    ✅ Payment SUCCESS: "
                f"{successful_payment.razorpay_payment_id}"
            )
            
            # Cleanup
            print("[10] Cleanup")
            db.delete(buyer_session)
            db.delete(buyer_profile)
            db.commit()
            print("    ✅ Test data cleaned up")

    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user.")
        return 0
    except Exception as exc:
        print()
        print("❌ PAYMENT SMOKE TEST FAILED")
        print(f"   {type(exc).__name__}: {exc}")
        return 1

    print_header("✅ UPLIFT REAL-TIME PAYMENT SMOKE TEST PASSED")
    print("Live path verified:")
    print("    Groq → Merchant Agent → deterministic pricing/policy")
    print("          → AI Buyer → dual authorization")
    print("          → Razorpay Order → Checkout")
    print("          → signature verification")
    print("          → reconciliation")
    print("          → Order PAID")
    print("          → Payment SUCCESS")
    print()
    print("Payment flow successfully exercised.")
    print("Check your Razorpay Dashboard for test transactions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())