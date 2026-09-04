## Day 4 — Module 1: Purchase Confirmation Contract ✅

### Summary

We added the structured contract for the AI Buyer's final approval/rejection:

```
PurchaseConfirmation
```

with:

```
approved: bool
amount_paise: int
```

The important rule is that `amount_paise` represents the **exact server-computed offer amount**. The confirmation contract itself has no payment side effects and cannot call Razorpay, matching the PRD.

We also added tests for:

```
✅ approval
✅ rejection
✅ negative amounts
✅ missing amount
✅ missing approval field
```

This established the data contract needed for the later dual-authorization step.

### Mistakes / Issues

The main issue was not implementation failure, but **scope discipline**: we had to make sure Module 1 only created the contract rather than prematurely implementing authorization or payment.

We correctly kept:

```
PurchaseConfirmation
        ↓
data/validation only
```

rather than:

```
PurchaseConfirmation
        ↓
Razorpay
```

### Engineering Lesson

> **A confirmation object is not authorization by itself.**

The system needs a structured representation of the buyer's decision first, and a separate deterministic authorization layer later.

---

# Day 4 — Module 2: AI Buyer Offer Evaluation ✅

### Summary

We built:

```
AIBuyer
```

with:

```
evaluate_offer(...)
```

The buyer now evaluates a Merchant Agent `PurchaseOffer` against the buyer's budget and the merchant policy result.

The logic is:

```
Offer
  ↓
Is it above buyer budget?
  ├─ yes → reject
  └─ no
       ↓
Is policy REJECTED?
  ├─ yes → reject
  └─ no → approve
```

The important part is that the buyer **does not alter the amount**.

Example:

```
Server offer: ₹899
Buyer budget: ₹1,000

→ approved=True
→ amount_paise=89900
```

But:

```
Server offer: ₹899
Buyer budget: ₹500

→ approved=False
→ amount_paise=89900
```

So the buyer's approval is always tied to the exact server-computed amount. That matches the PRD requirement that the AI Buyer evaluate the Merchant Agent's offer and explicitly approve/reject the exact amount.

We tested:

```
✅ offer within budget
✅ offer above budget
✅ REJECTED policy result
✅ REQUIRES_CONFIRMATION offer
✅ missing buyer budget
✅ exact amount preservation
```

### Mistakes / Issues

The main subtlety was distinguishing:

```
REJECTED
```

from:

```
REQUIRES_CONFIRMATION
```

We did **not** incorrectly treat every non-`ALLOWED` result as an automatic rejection.

`REJECTED` means the offer cannot proceed.

`REQUIRES_CONFIRMATION` means another authorization requirement exists; the later authorization layer determines whether the transaction can proceed.

That distinction is important because the policy engine already explicitly returns both states.

### Engineering Lesson

> **The AI Buyer evaluates; it does not authorize payment.**

Its responsibility is essentially:

```
Does this exact offer fit the buyer's constraints?
```

The eventual authorization layer must answer:

```
Is the system legally/architecturally allowed to send this exact approved amount to Razorpay?
```

That separation keeps both agents outside the actual money authority, as required by the project's architecture.

![[Pasted image 20260903213428.png]]

## Day 4 — Module 3: Dual Authorization ✅

### Summary

We added the deterministic authorization gate:

```
authorize_purchase(
    offer=...,
    confirmation=...
)
```

It checks three critical conditions:

```
1. Merchant policy is not REJECTED
2. AI Buyer explicitly approved
3. Approved amount == exact server-computed offer amount
```

So the final gate is:

```
PurchaseOffer
      +
PurchaseConfirmation
      ↓
authorize_purchase()
      ↓
TRUE
      ↓
payment layer can proceed
```

The important invariant is:

```
merchant policy
AND
buyer exact-amount approval
```

Both are required before payment. The PRD explicitly requires exact buyer approval and keeps Razorpay behind the authorization boundary.

We also tested:

```
✅ allowed + exact approval
✅ buyer rejection
✅ wrong approved amount
✅ policy rejection
✅ requires-confirmation + exact approval
✅ mismatched amounts
✅ unknown policy status
```

### Mistakes / Issues

The main thing we had to avoid was treating:

```
approved=True
```

as sufficient authorization.

It isn't.

A buyer can approve an amount that does not match the current server offer:

```
Offer:        ₹899
Buyer says:   ₹799 approved
```

That must be rejected.

We also deliberately did **not** connect this function directly to Razorpay yet. Authorization and payment execution remain separate layers, consistent with the PRD's security boundary.

### Engineering Lesson

> **Authorization is a conjunction, not a single approval.**

In Uplift:

```
Merchant permission
        AND
Buyer permission
        AND
Exact amount match
        ↓
Payment authorization
```

This is the core distinction between an agent **making a decision** and the system **being allowed to move money**.
![[Pasted image 20260904002725.png]]

## Day 4 — Module 4: Backend Workflow Orchestration ✅

### Summary

We connected the Day 4 components into one backend workflow:

```
PurchaseRequest
      ↓
MerchantAgent
      ↓
PurchaseOffer
      ↓
AIBuyer
      ↓
PurchaseConfirmation
      ↓
Dual Authorization
      ↓
create_order()
      ↓
Razorpay
```

We added:

```
apps/api/agents/workflow.py
tests/unit/test_workflow.py
```

The `PurchaseWorkflow` coordinates four stages:

```
prepare_offer()
→ Merchant Agent

evaluate_offer()
→ AI Buyer

authorize()
→ Dual-authorization gate

create_authorized_order()
→ existing payment service
```

The critical safety property is that **`create_order()` cannot run unless authorization succeeds**. The payment amount passed to it is taken from the server-computed `PurchaseOffer.amount_paise`, not from the LLM or buyer. This matches the PRD's architecture in which both agents sit above the deterministic money layer.

The tests verify:

```
✅ authorized flow reaches create_order
✅ rejected buyer cannot create an order
✅ Merchant Agent → Buyer → Authorization are connected
✅ exact amount is preserved
✅ unauthorized flow never reaches Razorpay
```

### Mistakes / Issues

There were no test failures reported for Module 4.

The main architectural issue we had to guard against was **letting the workflow itself become a money authority**.

We deliberately avoided:

```
LLM → create_order
```

and instead kept:

```
LLM
 ↓
structured proposal
 ↓
deterministic offer
 ↓
buyer confirmation
 ↓
authorization
 ↓
create_order
```

Another important distinction was not confusing **workflow orchestration** with **payment implementation**. The workflow calls the existing payment boundary rather than duplicating Razorpay logic.

### Engineering Lesson

> **Orchestration should connect authority boundaries, not replace them.**

Each component has one responsibility:

```
Merchant Agent   → proposes
AI Buyer         → evaluates / approves
Authorization    → decides whether both approvals are valid
Pricing          → owns amount
Policy           → owns merchant rules
create_order     → owns Razorpay access
```

That separation is what makes the agentic workflow safer than simply giving an LLM access to a payment API. The PRD explicitly requires the authorization boundary to prevent any code path from reaching Razorpay without the required merchant-policy and exact buyer approval
![[Pasted image 20260904003413.png]]

## ✅ Day 4 / Current Milestone Summary

We finished the **agentic commerce backend path** and then verified it with a real live payment.

The completed flow is now:

```
Natural buyer request
        ↓
Groq
        ↓
Merchant Agent
        ↓
deterministic catalog + upsell validation
        ↓
authoritative pricing
        ↓
Policy Engine
        ↓
AI Buyer evaluation
        ↓
exact-amount confirmation
        ↓
dual authorization
        ↓
Razorpay Order
        ↓
Standard Checkout
        ↓
Test Mode payment
        ↓
server-side signature verification
        ↓
reconciliation
        ↓
Order = PAID
Payment = SUCCESS
```

The final real smoke test successfully demonstrated:

```
✅ Groq structured output
✅ natural Merchant Agent selection
✅ budget-aware upsell selection
✅ ₹899 deterministic price
✅ policy ALLOWED
✅ AI Buyer approved
✅ exact amount preserved
✅ dual authorization
✅ Razorpay Test Mode Order
✅ Standard Checkout
✅ Test Mode card payment
✅ signature verification
✅ reconciliation
✅ Order PAID
✅ Payment SUCCESS
```

The latest transfer document captures the full implementation history and debugging trail.

---

# 🐛 Mistakes / Issues We Encountered

### 1. Merchant Agent wasn't budget-aware enough

Groq initially proposed baskets such as:

```
COL-002 ₹5,499
+
COL-003 ₹3,999
=
₹9,498
```

for a ₹5,000 budget.

The backend correctly blocked it, but the agent's proposal layer needed improvement.

**Fix:** expose deterministic prices, `max_autonomous`, and basket totals to the model, while still re-pricing the proposal server-side.

### 2. We almost made the payment test artificially deterministic

We considered telling the LLM:

```
choose MER-002
don't upsell
```

That would have defeated the purpose of testing the real agent.

**Lesson:** the positive smoke test should use a natural request and let Groq make the decision.

### 3. Wrong Razorpay client import

Used:

```
RazorpayClient
```

when the project actually exposes:

```
get_razorpay_client()
```

### 4. Windows Unicode encoding

Temporary checkout HTML contained Unicode characters and Windows `charmap` failed.

**Fix:**

```
open(..., encoding="utf-8")
```

### 5. Checkout callback URL was wrong

The HTML originally called:

```
/api/checkout/success
```

while the actual backend endpoint was:

```
/test/razorpay/verify
```

### 6. `file://` checkout caused CORS problems

The temporary HTML had origin:

```
null
```

which required temporary CORS handling.

This is acceptable for the local harness, but **not the final frontend architecture**.

### 7. Browser expected the wrong response shape

Frontend checked:

```
data.success
```

while backend returns:

```
{
  "status": "PAID"
}
```

### 8. Uvicorn didn't have the Razorpay secret

The smoke-test process had the credentials, but the separate Uvicorn process did not.

**Lesson:** separate processes have separate environments.

### 9. Smoke test falsely reported success

It previously printed:

```
PASSED
```

even when:

```
Order = CREATED
Payment = none
```

We fixed this so payment verification is a hard success condition.

### 10. Stale SQLModel session

The FastAPI verification process updated the Order to `PAID`, but the smoke-test process held a stale object.

**Fix:**

```
db.expire_all()
db.refresh(order)
```