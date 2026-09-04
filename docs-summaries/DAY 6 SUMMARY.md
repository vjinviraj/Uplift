### Module 1 summary

We verified that the existing Uplift system remains intact across backend and frontend after the Day 5 implementation. The backend remains the source of truth for pricing, policy, authorization, and payment, while the frontend consumes those results.

### Mistakes / issues found

The main issues were:

- stale Razorpay failure-response property access in TypeScript
- `useSearchParams()` not being inside a Suspense boundary for production builds
- two unused frontend variables
- an outdated logo path that we corrected while touching the file

Nothing required an architectural redesign.

### Engineering lesson

**A development server succeeding does not mean a Next.js production build will succeed.**

Production prerendering/type checking exposed issues that normal local rendering didn't. Running both:

```
uv run pytest
bun run lint
bun run build
```

is therefore part of the actual regression process, not just a final formality.

### Module 2 summary

We hardened the frontend failure → retry experience while preserving the backend safety boundary.

The flow is now clearly:

```
Payment failure
→ server records failure
→ failed Order remains identifiable
→ retry available
→ fresh Razorpay Order created
→ retry Order shown separately
→ retry limit enforced
```

This matches the required invariant:

```
failed Order ≠ retry Order
```

and the backend continues enforcing the single-retry limit and fresh idempotency key.

### Tests

You completed the requested:

```
Backend regression       ✅
Frontend lint            ✅
Frontend build           ✅
Failure → retry flow     ✅
Failed Order visibility  ✅
Fresh Retry Order        ✅
Retry limit              ✅
Audit trail              ✅
```

### Mistakes / issues

Nothing architectural was broken. The main lesson was that the **UI should make backend safety guarantees visible**, rather than merely implementing them invisibly.

### Engineering lesson

**The frontend is a presentation layer for security-sensitive state, not a second implementation of the security rules.**

The browser can show:

```
Order A failed
Order B is the retry
1 retry used
```

but the backend remains responsible for enforcing those facts. That separation is already part of Uplift's design.

### Module 3 summary

We successfully verified the complete real retry transaction:

```
Payment failure
→ failed Order
→ fresh retry Order
→ successful Test Mode payment
→ server-side signature verification
→ reconciliation
→ PAID / SUCCESS
→ audit trail
```

This confirms the retry path works end-to-end, not just at the UI level. It also validates the core invariant that a failed Order is never reused for the retry.

### Mistakes / issues

No code changes were required.

The important distinction we verified is:

```
Browser success ≠ payment truth
```

The backend's verification and reconciliation remain authoritative.

### Engineering lesson

**Integration testing should validate the entire state transition, not just whether an API returns 200.**

Here we proved:

```
Razorpay
→ backend verification
→ local DB state
→ frontend state
→ audit trail
```

all converge on the same final transaction state.

## Day 6 — Module 4 ✅ Complete

`uv run pytest` passes after the Module 4 hardening changes.

### What we implemented

- Durable `PurchaseApproval` database record.
- Exact approved amount stored server-side.
- `policy_version` stored with the approval.
- SHA-256 `offer_hash` binds approval to the exact `PurchaseOffer`.
- `extra_confirmation` added to the approval contract.
- `REQUIRES_CONFIRMATION` now requires explicit extra confirmation.
- Approval evidence is persisted before Razorpay order creation.
- Authorization verifies the durable approval before payment.
- `buyer_approval_recorded` audit evidence captures the approval context.
- Transaction details now use the durable approval record rather than inferring approval merely from order existence.

This directly closes the previously documented gap where `REQUIRES_CONFIRMATION + exact buyer approval` could otherwise pass without durable additional-confirmation evidence.

### Mistakes / issues we hit

The first implementation caused six regression failures.

The main mistake was making `create_authorized_order()` require a durable approval record while the existing isolated workflow tests still supplied only a mocked `Session` and transient `PurchaseConfirmation`. The old tests were written against the pre-hardening contract.

We also initially checked durable approval before authorization, which changed the expected error for rejected buyers. We corrected the ordering so the authorization gate still fails first.

### Engineering lesson

The important design principle here is:

```
Transient approval
        ≠
Trusted authorization evidence
```

For a payment-sensitive workflow, the server should be able to prove:

```
exact offer
+
exact amount
+
policy version
+
buyer approval
+
required extra confirmation
+
timestamp/evidence
        ↓
authorization
        ↓
payment
```

That fits the project's core invariant that pricing, policy, authorization, and payment remain deterministic backend responsibilities rather than LLM responsibilities.

