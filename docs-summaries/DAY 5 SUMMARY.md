## Module 1 Summary

**Goal:** Establish the final frontend foundation.

Completed:

```
Next.js 16.3.4          ✅
TypeScript              ✅
Tailwind CSS            ✅
App Router              ✅
src/ directory          ✅
Development server      ✅
Production build        ✅
```

The frontend now lives at:

```
uplift/
└── frontend/
```

with the Next.js application under:

```
frontend/src/app/
```

The existing backend was not changed, preserving the established architecture where the backend remains authoritative for pricing, policy, authorization, and payment execution.

## Module 1 Mistakes / Issues

### 1. We initially thought `/login` was a Next.js redirect

It wasn't.

The browser was retaining localhost site state. We verified this properly by hitting the server directly:

```
GET /
→ 200 OK
→ default Next.js page

GET /login
→ 404
```

Clearing the Brave `localhost` site data fixed it.

**Lesson:** distinguish browser state from application behavior before changing application code.

### 2. We nearly treated the frontend directory as unknown state

The `frontend` directory existed but was empty, so the correct move was to inspect it rather than assume an existing app needed modification.

### 3. Nothing was actually wrong with the Next.js scaffold

The generated `page.tsx`, `layout.tsx`, and `next.config.ts` were all clean defaults. No unnecessary code changes were made.

## Engineering Lesson

The main lesson from this module is:

> **Verify the system at the correct layer before modifying it.**

We checked:

```
Browser
   ↓
HTTP response
   ↓
Next.js routing
   ↓
Source files
```

and only then changed browser state.

That same discipline matters for Uplift's payment architecture too: the browser is not payment truth; server-side verification and reconciliation are.

# Module 2 — Summary

### What we completed

Module 2 established the **frontend visual foundation and polished Uplift checkout shell**.

We reset the frontend UI work and rebuilt it cleanly on top of the working Next.js/shadcn scaffold.

The completed pieces are:

```
Next.js frontend
    ↓
Tailwind + shadcn foundation
    ↓
Uplift AppShell
    ├── Sidebar
    ├── Workspace navigation
    ├── Demo section
    └── TEST MODE indicator
    ↓
AI Buyer Checkout screen
    ├── AI Buyer request
    ├── Budget
    ├── Product
    ├── Upsell
    ├── Server-computed price
    ├── Approve / Reject UI
    ├── Live Agent Workflow
    ├── Why This Upsell?
    └── Money Safety
```

The structure follows the frontend design specification's intended checkout composition and application shell.

### Final verification

```
bun run lint
✅ 0 errors
✅ 0 warnings

bun run build
✅ Compiled successfully
✅ TypeScript passed
✅ Static generation passed
✅ Production build passed
```

So **Module 2 is technically complete and the frontend builds successfully**.

### Important architectural boundary

The frontend currently represents the workflow visually. It does **not** own authoritative commerce decisions.

The intended boundary remains:

```
Frontend
   ↓
API
   ↓
FastAPI backend
   ↓
Deterministic workflow / agents
   ↓
Price / policy / authorization / payment truth
```

This preserves the project's core invariant that the LLM proposes/evaluates while deterministic backend code owns the money and authorization boundary.

---

# Mistakes / Issues

### 1. Initial implementation had unnecessary imports

We initially imported `Badge` and `Separator` without using them, producing lint warnings.

**Fixed:** removed the unused imports.

### 2. Lucide component typing mistake

We created an `ActivityIcon` wrapper function and passed it where a Lucide component was expected.

That caused:

```
Property '$$typeof' is missing...
```

**Fixed:** passed the actual `Activity` Lucide component directly.

### 3. Tailwind IntelliSense warning

VS Code reported:

```
size-[22px] can be written as size-5.5
```

This was **not a build failure**; it was only a Tailwind IntelliSense canonical-class suggestion.

The rebuilt code avoids that unnecessary arbitrary sizing.

### 4. Stale Turbopack runtime cache

The development server temporarily produced the `next/image.js [app-rsc]` module-factory error even though the page itself wasn't intentionally using `next/image`.

**Fixed:** cleared `.next`/development cache and restarted the dev server.

### 5. Mockup data inconsistency

The earlier visual mockup used:

```
Budget: ₹2,500
Product: ₹1,999
Upsell: ₹899
Total: ₹2,898
```

while visually presenting an approval flow despite being over budget.

We rebuilt the example using the coherent PRD scenario:

```
EA Sports FC       ₹999
Gaming Controller ₹1,499
────────────────────────
Total             ₹2,498
Budget            ₹2,500
```

The PRD's example explicitly uses the ₹999 + ₹1,499 = ₹2,498 scenario.

## Day 5 — Module 3 Summary

### What we completed

Module 3 connected the polished Next.js frontend to the existing FastAPI backend through a dedicated frontend API/types layer, without moving any money authority into the browser.

The target flow was:

```
AI Buyer request
    ↓
Frontend API
    ↓
FastAPI
    ↓
PurchaseWorkflow
    ↓
Merchant Agent
    ↓
deterministic pricing + policy
    ↓
PurchaseOffer
    ↓
exact buyer approval
    ↓
authorization
    ↓
Razorpay Order
```

This is the exact direction specified for Module 3: inspect the existing backend contracts, create the frontend API boundary, wire the checkout request, render the backend offer, and submit the exact buyer approval.

### What we proved manually

Your browser successfully reached:

```
POST /api/purchases/prepare
```

and the flow progressed all the way to:

```
Razorpay
Test Mode order created
order_...
```

So the frontend/backend connection and backend workflow are functioning far enough to create a real Razorpay Test Mode order.

The fact that the UI stopped at the Razorpay Order ID is **expected for this module**. Browser Checkout, payment verification, reconciliation, success/failure states, and retry UI are subsequent work.

### Module 3 architectural result

The important boundary remains:

```
Frontend
→ requests + displays state

Backend
→ price
→ policy
→ approval validation
→ authorization
→ payment execution
```

The frontend must not become authoritative for price, policy, approval truth, verification, or reconciliation.

---

# Mistakes / Issues

### 1. Environment variable wasn't loaded

The first browser attempt returned:

```
400 Bad Request
GROQ_API_KEY is not configured
```

The backend currently uses `os.getenv()` and does not automatically load `.env` files, so the API key had to be supplied to the backend process environment.

**Lesson:** Local environment configuration is part of the runtime contract. A working `.env` file sitting on disk is not enough when the application doesn't load it.

### 2. We initially expected the flow to continue past Razorpay Order creation

You saw:

```
Test Mode order created.
order_...
```

and reasonably expected the payment screen to open.

That wasn't a bug in the Module 3 result. We had reached the boundary intentionally; the browser Checkout integration is the next stage. The planned frontend sequence explicitly separates API integration from browser Checkout and verification.

**Lesson:** Separate backend-order creation from browser payment execution. An Order ID existing does not mean the payment flow has started.

### 3. We had to be careful not to reuse the old temporary Razorpay endpoints

The project still contains temporary `/test/razorpay/*` harnesses, but those are explicitly not the final product API.

**Lesson:** Integration/debug endpoints and product APIs should remain conceptually separate.

---

## Engineering takeaway

Module 3 established the critical bridge:

> **The frontend is now a consumer of the agentic commerce backend rather than a second implementation of the commerce logic.**

That preserves the project's main invariant: **LLMs propose/evaluate; deterministic backend code owns price, policy, authorization, and payment execution.**

# Day 5 — Module 4 Summary

### What we completed

Module 4 connected the frontend to the **real Razorpay Standard Checkout** instead of stopping at Order creation.

The completed path is:

```
Buyer approval
      ↓
Razorpay Order
      ↓
Razorpay Standard Checkout
      ↓
Test Mode payment
      ↓
Razorpay payment response
      ↓
Backend signature verification
      ↓
Backend reconciliation
      ↓
PAID / SUCCESS
```

This matches the project's required journey and preserves the rule that a browser-side success response is **not** considered final payment truth.

### What we actually verified

You completed a real Test Mode payment and received:

```
Payment verified and reconciled.

order_TY0fHLbXelAnLX

Payment signature verified and order reconciled.
```

So Module 4 successfully demonstrated:

```
✅ Razorpay Checkout opened
✅ Test payment completed
✅ Razorpay response returned
✅ Backend received payment identifiers
✅ Signature verified server-side
✅ Payment reconciled
✅ Order reached successful state
```

The broader project documentation identifies real Standard Checkout, server-side signature verification, and reconciliation as essential parts of the end-to-end payment flow.

---

# Mistakes / Issues

### 1. We initially treated Order creation as the end of the frontend payment step

In Module 3 the UI stopped at:

```
Test Mode order created.
order_...
```

It looked like something was missing because Checkout had not opened.

The distinction was:

```
Create Order
≠
Complete Payment
```

Module 4 correctly added the browser Checkout layer.

### 2. The frontend must not trust its own payment success state

A successful browser callback is only an input to the backend.

The secure path is:

```
Browser callback
      ↓
backend verification
      ↓
reconciliation
      ↓
local PAID state
```

The existing architecture explicitly treats server-side verification/reconciliation as the payment truth.

### 3. We had to preserve the temporary-vs-final API separation

The older Razorpay `/test/razorpay/*` endpoints exist as integration harnesses, but they are not intended to become the final frontend API.

The frontend now uses the product-facing payment flow instead of making the temporary harness the permanent architecture.

---

# Engineering Lesson

The biggest lesson from Module 4 is:

> **Payment UI is not payment truth.**

The browser can initiate Checkout and report what Razorpay returned, but the backend must independently verify the response and reconcile the payment before Uplift considers the transaction successful.

So the trust boundary is:

```
Frontend
  = presentation + user interaction

Razorpay
  = external payment processor

Backend
  = payment truth
```

This fits Uplift's broader architectural principle:

> **LLMs propose or evaluate. Deterministic backend code owns price, policy, authorization, and payment execution.**

