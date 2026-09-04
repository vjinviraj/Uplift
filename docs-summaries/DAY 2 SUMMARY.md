# Module 1 Summary ✅

### What we built

- Added the `Order` SQLModel for payment/order-domain persistence.
- Added the `Payment` SQLModel for storing payment results and verification state.
- Kept authoritative money as **integer paise**, consistent with the existing architecture.
- Added TDD tests covering the required `Order` and `Payment` fields/defaults.
- Confirmed the new tests pass.
- Confirmed the existing Day 1 functionality remains intact through the full test suite.

The CTD defines these as the first two Day 2 payment-domain models, with `Order` carrying the authoritative order amount and Razorpay order/idempotency information, and `Payment` carrying Razorpay payment/status/verification information.

### What we learned

The important architectural boundary remains:

```
Day 1 deterministic commerce
        ↓
Order / Payment persistence
        ↓
Razorpay integration
```

We have **not** mixed Razorpay API logic into the models. The models are only responsible for representing persisted payment-domain state.

### Mistakes / issues

The only issue encountered was the intentional TDD failure:

```
ImportError: cannot import name 'Order'
```

That happened because the tests were written before the models existed. This was **expected and correct** for the red phase of TDD.

There were **no actual implementation mistakes** during Module 1.

# Module 2: Razorpay Client / Configuration

Module 2 is now complete.

```
Razorpay SDK 2.0.1              ✅
Razorpay client boundary        ✅
Environment-based credentials   ✅
.env.example placeholders       ✅
Missing-credential test         ✅
Client initialization test      ✅
Full regression suite           ✅
```

The latest CTD places these items in Module 2 and keeps the actual order creation, signature verification, failure/retry, and idempotency work for the subsequent Razorpay steps.

### Mistakes / Fixes

- **Incorrect version verification command**
    - I initially used `razorpay.__version__`.
    - The module doesn't expose that attribute.
    - Fixed by verifying through `uv pip show razorpay`.
- No project-side implementation errors were encountered in this module.

# Module 3 Summary 

### What we built

- Added the `create_razorpay_order()` helper.
- Validated that `amount_paise` must be greater than zero.
- Passed the authoritative integer paise amount directly to Razorpay.
- Added the local `Order` persistence flow.
- Connected the Razorpay-created order ID to our local `Order` record.
- Persisted:
    - `session_id`
    - `amount_paise`
    - `currency`
    - `status`
    - `razorpay_order_id`
    - `idempotency_key`
- Added application-level idempotency protection.
- Rejected duplicate `idempotency_key` values **before making another Razorpay order request**.
- Verified that different idempotency keys can create separate orders.
- Full regression suite reached **50 passed**.

This matches the CTD's Day 2 requirement for authorized order creation, authoritative amounts, receipt/idempotency handling, and duplicate-order protection.

### Flow established

```
authoritative amount
        ↓
create_razorpay_order()
        ↓
Razorpay order response
        ↓
local Order record
        ↓
SQLite
```

With idempotency:

```
idempotency_key
      ↓
existing Order?
   ↙       ↘
 yes       no
  ↓         ↓
reject    create
```

### Mistakes / Fixes

There were no major project-side mistakes in Module 3.

One thing to note is that the initial implementation used the provided `idempotency_key` as the Razorpay `receipt`. That was intentional for the current bounded demo flow, while proper end-to-end idempotency behavior remains part of the broader Razorpay work.

# Module 4 Summary ✅

### What we built

- Implemented Razorpay payment-signature verification.
- Used the documented HMAC-SHA256 verification flow.
- Validated the signature against:
    
    ```
    order_id|payment_id
    ```
    
    using the Razorpay secret.
    
- Rejected missing signatures.
- Rejected tampered/invalid signatures.
- Used `hmac.compare_digest()` for the final comparison.
- Added TDD coverage for all three required cases.
- Full regression suite remains green at **53 passed**.

The latest CTD explicitly requires valid, tampered, and missing signature tests as part of the Day 2 Razorpay work.

### Current Day 2

```
Module 1 — Order + Payment Models       ✅
Module 2 — Razorpay Client / Config     ✅
Module 3 — Order Creation               ✅
Module 4 — Signature Verification       ✅
Module 5 — Failure + Retry              ⬜
Module 6 — Day 2 E2E / final checks     ⬜
```

### Mistakes / Fixes

- **Incorrect initial valid-signature test**
    - I initially gave you an empty signature fixture.
    - That was incomplete because the actual signing algorithm had not yet been established.
    - We corrected it using the documented HMAC-SHA256 rule.
- **Incorrect SDK version check earlier**
    - I initially used `razorpay.__version__`.
    - The module does not expose that attribute.
    - We verified the package correctly with `uv pip show razorpay`, confirming **2.0.1**.

No project-side implementation mistake occurred in Module 4.

## Module 5 — Payment Failure + Bounded Retry ✅

### Summary

- Added `MAX_PAYMENT_RETRIES = 1`.
    
- Implemented `handle_payment_failure()`.
    
- Implemented `retry_order()` with:
    
    - fresh Razorpay Order
        
    - new idempotency key
        
    - same authoritative amount
        
    - retry-limit enforcement
        
    - only `PAYMENT_FAILED` orders can retry
        
- Implemented `record_payment_failure()`.
    
- Payment failure now:
    
    - marks `Order` as `PAYMENT_FAILED`
        
    - creates `Payment` with `FAILED`
        
    - stores `failure_reason`
        
    - validates required payment fields
        
- Added audit events:
    
    - `payment_failed`
        
    - `retry_started`
        
    - `retry_exhausted`
        
- Added `tests/conftest.py` with an isolated SQLite session fixture.
    
- Expanded `tests/unit/test_payment_failure.py`.
    
- All Module 5 tests passed, and the full suite passed.
    

### Mistakes / Fixes

- **Missing `session` fixture**
    
    - Added `tests/conftest.py`.
        
- **Failure reason initially targeted at `Order`**
    
    - Corrected to `Payment.failure_reason`.
        
- **`agent_run_id` made mandatory**
    
    - Broke existing tests.
        
    - Changed to `agent_run_id="system"` by default.
        
- **`record_audit_event()` lacked Razorpay ID parameters**
    
    - Added `razorpay_order_id` and `razorpay_payment_id`.
        
- **Razorpay IDs initially stored only in `payload_json`**
    
    - Corrected to use the dedicated audit fields.
        
- **Retry logic initially needed clearer separation**
    
    - Ensured the failed order remains unchanged and retry creates a separate fresh order.
        

### Key invariant

```text
payment failure
→ PAYMENT_FAILED
→ exactly one retry
→ fresh Razorpay Order
→ same authoritative amount
→ no third automatic retry
```

The PRD defines the same one-retry boundary and fresh-order recovery behavior.

## Module 6 — Final E2E Verification ✅

### Summary

- Built `reconcile_payment()`.
    
- Verified captured payments against the **authoritative amount**.
    
- Ignored failed/non-captured attempts.
    
- Handled multiple payment attempts correctly.
    
- Updated local `Payment` to `SUCCESS`.
    
- Set `verified_at`.
    
- Updated local `Order` to `PAID`.
    
- Added `payment_reconciled` audit coverage.
    
- Added Day 2 flow tests for success and failure/retry behavior.
    
- Final full test suite passed.
    

### Mistakes / Fixes

- **Missing reconciliation module**
    
    - Created `razorpay_client/reconciliation.py`.
        
- **Old test signature**
    
    - Tests initially used `razorpay_order_id`.
        
    - Updated to use `session + order`.
        
- **Missing local Payment record**
    
    - Reconciliation correctly requires a matching local `Payment`.
        
    - Added the required test records.
        
- **Timezone assertion**
    
    - SQLite returned persisted `verified_at` without `tzinfo`.
        
    - Removed the unnecessary timezone-specific assertion.
        
- **Wrong captured payment stopped reconciliation**
    
    - Initial implementation raised immediately.
        
    - Changed it to continue searching for a later captured payment with the correct amount.
        
- **Razorpay IDs in audit payload instead of dedicated fields**
    
    - Fixed `record_audit_event()` to populate dedicated Razorpay fields.
        

### Module 6 result

```text
✅ Reconciliation tests passing
✅ Day 2 regression passing
✅ Module 6 unit/E2E verification complete
```


# Day 2 — Razorpay Integration Module Summary

Day 2 focused on taking the deterministic commerce backend from **local/unit-tested payment logic to a real Razorpay Test Mode transaction flow**.

### What we completed ✅

```text
Order + Payment models
        ↓
Razorpay client/config
        ↓
Razorpay Order creation
        ↓
Signature verification
        ↓
Payment reconciliation
        ↓
Real Standard Checkout
        ↓
Real successful Test Mode payment
        ↓
Real failed Test Mode payment
        ↓
Failure persistence
        ↓
Fresh retry Order
```

The backend now supports:

- `Order` and `Payment` persistence.
    
- Razorpay SDK integration.
    
- Application-level idempotency.
    
- HMAC-SHA256 payment signature verification.
    
- Server-side payment reconciliation.
    
- Exact authoritative amount checking.
    
- `PAYMENT_FAILED` / `FAILED` state handling.
    
- Failure reason persistence.
    
- Append-only payment audit events.
    
- Maximum **one** retry.
    
- Fresh Razorpay Order for the retry.
    
- Same authoritative amount on retry.
    

The real-world Razorpay flow was successfully demonstrated:

**Success**

```text
Order #1
₹899
→ Razorpay Checkout
→ successful Test payment
→ signature verification
→ reconciliation
→ Order = PAID
→ Payment = SUCCESS
```

**Failure**

```text
Order #3
₹899
→ Razorpay Checkout
→ deliberate card failure
→ Razorpay server confirms failed payment
→ Order = PAYMENT_FAILED
→ Payment = FAILED
→ failure_reason = payment_failed
```

**Retry**

```text
Order #3
PAYMENT_FAILED
→ retry_order()
→ Order #4
→ new Razorpay Order
→ order_TXFjoM5ukLmJ19
→ same ₹899
```

The retry **payment itself still needs to be completed and verified**.

---

# Mistakes / Problems Encountered ⚠️

### 1. Assuming `.env` was automatically loaded

We initially checked:

```powershell
$env:RAZORPAY_KEY_ID
$env:RAZORPAY_KEY_SECRET
```

and both were empty.

The credentials were actually in `.env`.

**Lesson:** `os.getenv()` does not automatically read `.env`.

We temporarily loaded the `.env` values into the PowerShell process instead of immediately adding a dependency.

---

### 2. Trying to force UPI when the merchant account didn't have it

The Razorpay Test Checkout showed:

```text
UPI transactions are not enabled for the merchant
```

We spent time investigating Payment Methods / Live Mode / UPI configuration.

Eventually we decided:

```text
UPI unavailable
→ don't block the project
→ continue with Test Mode Cards
```

**Lesson:** don't let an account-level limitation derail the MVP or switch to Live Mode just to bypass Test Mode configuration.

UPI remains an **uncompleted/unsupported part of the current demo**, not something to claim as implemented.

---

### 3. Building too much into the temporary checkout harness

We tried to make the temporary HTML page retain Razorpay failure data using `localStorage`.

Razorpay's checkout navigation meant the failure callback wasn't reliably surviving the checkout flow.

**Lesson:** the browser is not the authoritative payment state. Use Razorpay's server-side payment records for reconciliation and failure confirmation.

---

### 4. Querying Razorpay with the wrong Order ID

We had:

```text
order_TXFiTBtMiXFoA
```

but Razorpay's actual order was:

```text
order_TXFItBtbMiXfoA
```

The capitalization differed.

Razorpay returned errors such as:

```text
not a valid id
```

**Lesson:** Razorpay IDs are case-sensitive. Never manually alter/retype them.

---

### 5. Misinterpreting the first failed checkout

The first failure popup appeared, but querying the corresponding order showed:

```text
attempts: 0
payments: []
```

So there was no server-confirmed failed payment for that order.

We initially considered it a successful failure-path test too early.

**Lesson:**

```text
Browser says "Payment Failed"
≠
server-confirmed failed payment
```

Always verify against Razorpay's server-side state.

---

### 6. Running a live retry script with `pytest`

We created:

```text
scripts/test_real_retry.py
```

Then ran:

```powershell
uv run pytest
```

Pytest automatically collected the script because it matched the `test_*.py` naming pattern.

It executed the **real Razorpay retry again**, which reused:

```text
real-retry-order-003
```

and correctly failed with:

```text
ValueError: Idempotency key already exists
```

This was **not a bug in idempotency or retry logic**.

**Lesson:**

Never name a live-execution script:

```text
test_*.py
```

unless it is actually a pytest test.

Correct cleanup:

```powershell
Rename-Item scripts\test_real_retry.py scripts\run_real_retry.py
```

---

### 7. Trying to diagnose the Razorpay SDK error without seeing the raw HTTP response

The SDK initially only showed:

```text
razorpay.errors.ServerError
```

with an empty message.

We bypassed the SDK temporarily using `requests` to inspect the actual HTTP response.

**Lesson:** when an SDK hides useful error details, inspect the underlying HTTP response during diagnosis rather than modifying application logic blindly.

---

### 8. Temporary scripts initially had the same Python import-path problem

Running:

```powershell
uv run python scripts/debug_razorpay_failure.py
```

produced:

```text
ModuleNotFoundError: No module named 'apps'
```

The project convention is:

```powershell
uv run python -m scripts.debug_razorpay_failure
```

**Lesson:** run project scripts as modules. Don't use `sys.path` hacks.

---

### 9. We almost treated reconciliation as broken when the real issue was the Order ID

The reconciliation code was already correct and unit-tested.

The actual problem was the incorrect/case-mismatched Razorpay Order ID.

**Lesson:** verify external identifiers before redesigning working backend logic.

---

### 10. Using a shared request model for failure and success

The success request requires:

```python
razorpay_signature
```

but a failed payment doesn't use that same success-signature contract.

We corrected this by introducing:

```python
class PaymentFailureRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
```

**Lesson:** success and failure are different payment contracts and should not be forced into one schema.

---

### 11. Initially missing an important paid-order guard

The failure endpoint could theoretically attempt to turn a paid Order back into:

```text
PAYMENT_FAILED
```

We added:

```python
if order.status == "PAID":
    raise HTTPException(
        status_code=409,
        detail="Order is already paid",
    )
```

**Lesson:** payment state transitions need explicit invariants, not just happy-path logic.

---

### 12. Failure endpoint needed authoritative amount validation

We added:

```python
if failed_payment.get("amount") != order.amount_paise:
    raise HTTPException(
        status_code=400,
        detail="Failed payment amount does not match order amount",
    )
```

**Lesson:** even for failures, don't trust the browser's claimed transaction details. Match against the authoritative local Order and Razorpay record.

---

### 13. We didn't immediately treat the temporary integration endpoints as final architecture

We added:

```text
/test/razorpay/order
/test/razorpay/verify
/test/razorpay/failure
```

because we needed a fast Day 2 integration harness.

These are **temporary**, not the final Uplift API architecture.

**Lesson:** integration scaffolding is fine, but it should be cleaned up when the real orchestration/frontend is built.

---

# Biggest Lessons From Day 2

The most important ones are:

```text
1. The server is the payment authority.
2. Browser callbacks are not the final source of truth.
3. Never trust client-provided amounts.
4. Payment IDs/order IDs must be used exactly as returned.
5. Idempotency must prevent duplicate payment/order creation.
6. Retries must be bounded.
7. A retry should create a fresh Razorpay Order.
8. External integration scripts must stay separate from pytest discovery.
9. Don't redesign working code before validating identifiers and external state.
10. Keep temporary integration code separate from the final architecture.
```

### Current Day 2 status

```text
Order + Payment models              ✅
Razorpay client                     ✅
Order creation                      ✅
Signature verification              ✅
Failure handling                    ✅
Reconciliation                      ✅
Real Test Mode success              ✅
Real Test Mode failure              ✅
Real retry Order creation            ✅
Retry payment + reconciliation       ⬜
Final regression suite              ⬜
```

The **next immediate task** is therefore to rename the live retry script, rerun `uv run pytest`, then complete and reconcile the successful payment on:

```text
order_TXFjoM5ukLmJ19
```

The detailed CTD-3 already captures this full Day 2 history and exact resume point.