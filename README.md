# Uplift

<p align="center">
  <img src="frontend/public/brand/uplift-logo.png" alt="Uplift logo" width="520">
</p>

<p align="center">
  <strong>Agentic Upsell and Checkout Copilot for Gaming Commerce</strong>
</p>

<p align="center">
  AI-assisted product discovery, bounded upselling, safe authorization, and Razorpay checkout.
</p>

## Overview

Uplift is an agentic upsell and checkout system for gaming commerce.

Uplift connects an AI Buyer to a gaming merchant through a controlled commerce workflow. The buyer sends a natural-language request with a budget. A Merchant Agent finds a valid product and may propose one relevant upsell. The backend calculates the final amount, checks merchant policy, records buyer approval, creates the Razorpay Test Mode order, verifies the payment on the server, and records the transaction.

The key design rule is:

> **LLMs propose or evaluate. Deterministic backend code owns price, policy, authorization, and payment execution.**

The current MVP includes the full core purchase flow, Razorpay Test Mode checkout, server-side payment verification, bounded payment retry, durable approval evidence, audit logging, dashboards, scenario controls, product imagery, and experiment measurement.

## Problem

Traditional ecommerce catalogs are designed for human browsing. An AI buyer needs a structured way to:

1. Express product intent.
2. Include a budget and preferences.
3. Discover valid products.
4. Receive a relevant upsell.
5. See the exact server-computed amount.
6. Approve or reject the amount.
7. Complete payment.
8. Recover safely from one failed payment.
9. Produce an auditable transaction record.

Uplift demonstrates this workflow without giving an LLM direct authority over money.

## Product Flow

```text
AI Buyer
   |
   v
Purchase Request
   |
   v
Merchant Agent
   |
   +--> Search Catalog
   |
   +--> Get Upsell Candidates
   |
   +--> Validate Proposal
   |
   v
Deterministic Pricing
   |
   v
Merchant Policy
   |
   v
Purchase Offer
   |
   v
AI Buyer Approval
   |
   v
Dual Authorization
   |
   v
Durable Purchase Approval
   |
   v
Razorpay Order
   |
   v
Razorpay Standard Checkout
   |
   v
Server-side Signature Verification
   |
   v
Razorpay Reconciliation
   |
   +--> PAID
   |
   +--> PAYMENT_FAILED
            |
            v
       One Fresh Retry Order
   |
   v
Audit + Transaction + Measurement
```

## Why the Architecture Is Safe

Uplift separates AI reasoning from money authority.

### The AI Buyer can

- Generate or carry a controlled purchase request.
- Carry a maximum budget.
- Include category, platform, or franchise preferences.
- Evaluate the merchant offer.
- Approve or reject the exact server-computed amount.

### The Merchant Agent can

- Interpret buyer intent.
- Search the structured catalog.
- Select a valid base product.
- Read deterministic upsell candidates.
- Propose at most one upsell.
- Explain why the upsell is relevant.

### AI agents cannot

- Set the final price.
- Invent products.
- Invent compatibility.
- Invent discounts.
- Override merchant policy.
- Create the authoritative payment state.
- Decide that a payment succeeded.
- Call Razorpay directly.

### The backend owns

- Catalog truth.
- Price calculation.
- Policy enforcement.
- Buyer authorization checks.
- Razorpay order creation.
- Payment verification.
- Payment reconciliation.
- Retry limits.
- Audit records.

## Core Features

### AI-native purchase intent

The buyer can send requests such as:

```text
I want EA Sports FC under ₹2,500.
```

The request is converted into a validated structured purchase flow.

### Structured gaming catalog

The catalog contains 30 seeded products across:

- Games
- Consoles and hardware
- Controllers and peripherals
- Accessories
- Gaming merchandise
- Collectibles

Upsell candidates come from merchant-defined relationships such as:

- `compatible_with`
- `frequently_bought_with`

The system does not allow the LLM to invent a relationship.

### Bounded upsell

Uplift can add at most one upsell to a session.

The seeded policy also limits the maximum autonomous upsell item value to ₹1,000.

### Deterministic pricing

All money values use integer paise.

The backend calculates the authoritative order amount from trusted catalog data. The frontend and LLM output are not authoritative.

### Policy engine

The policy engine can reject unsafe money actions and can require extra buyer confirmation for orders that cross the normal autonomous order limit.

The seeded configuration includes a normal maximum order value of ₹5,000 before extra confirmation is required.

### Dual authorization

A payment action requires the correct merchant-side authorization state and explicit buyer approval for the same server-computed offer.

The approval is persisted as durable evidence and linked to the offer state.

### Razorpay Test Mode

Uplift uses Razorpay Test Mode for checkout.

The flow includes:

- Razorpay Order creation.
- Browser Standard Checkout.
- Server-side signature verification.
- Server-side reconciliation.
- Failure handling.
- One bounded retry with a fresh Razorpay Order.

A failed order is not reused for the retry.

### Audit trail

Important state changes are recorded as append-only audit events.

The audit trail supports:

- Agent decisions.
- Policy decisions.
- Buyer approval.
- Payment events.
- Retry events.
- Transaction state changes.

### Merchant dashboard

The frontend includes:

- Overview
- Scenario Selector
- Checkout
- Transaction Detail
- Audit Log
- Experiment Summary

Product and brand imagery is included in the checkout experience.

## Supported Demo Scenarios

The frontend provides controlled scenarios for demo and validation:

| Scenario | Purpose |
|---|---|
| `successful_upsell` | Normal purchase with one relevant upsell |
| `no_upsell` | Purchase without an upsell |
| `over_budget` | Buyer budget blocks an unsafe offer |
| `policy_rejection` | Merchant policy blocks the action |
| `payment_failure` | Failed payment followed by one bounded retry |

Scenario selection changes controlled demo inputs. It does not bypass backend safety rules.

## Technical Stack

### Backend

| Technology | Version / Status | Purpose |
|---|---|---|
| Python | 3.13.9 | Backend runtime |
| uv | Current project tool | Package and environment management |
| FastAPI | 0.141.1 | HTTP API |
| SQLModel | 0.0.42 | ORM and data models |
| SQLite | Demo database | Local persistence |
| Pydantic | Project dependency | Validation and structured schemas |
| pytest | 9.1.1 | Automated testing |
| Uvicorn | Project dependency | ASGI server |
| httpx | Project dependency | API and test client |
| Razorpay Python SDK | 2.0.1 | Razorpay Test Mode integration |
| Groq SDK | Project dependency | LLM API access |
| Groq model | `openai/gpt-oss-20b` | Merchant Agent reasoning |

### Frontend

| Technology | Version / Status | Purpose |
|---|---|---|
| Next.js | 16.3.4 | Web application |
| React | 19.2.8 | UI |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Styling |
| shadcn/ui | base-nova | UI components |
| lucide-react | Project dependency | Icons |
| Bun | 1.3.14 | Frontend package and runtime tooling |
| Razorpay Checkout | Test Mode | Browser payment UI |

## Project Structure

```text
apps/
└── api/
    ├── main.py
    ├── models.py
    ├── agents/
    │   ├── authorization.py
    │   ├── merchant_agent.py
    │   ├── schemas.py
    │   ├── workflow.py
    │   ├── llm_client.py
    │   └── tool_schemas.py
    ├── commerce/
    │   └── catalog.py
    └── policy/
        └── engine.py

tests/
├── conftest.py
└── unit/
    ├── test_authorization.py
    ├── test_workflow.py
    ├── test_payment_retry.py
    ├── test_purchase_api.py
    └── test_purchase_payment_api.py

frontend/
├── public/
│   ├── brand/
│   │   └── uplift-logo.png
│   └── products/
└── src/
    ├── app/
    │   ├── page.tsx
    │   ├── scenario/
    │   ├── overview/
    │   ├── transactions/
    │   └── audit/
    ├── components/
    │   └── uplift/
    └── lib/
        ├── api.ts
        ├── razorpay.d.ts
        ├── scenarios.ts
        └── types.ts
```

## Setup

### Requirements

Install:

- Python 3.13
- uv
- Bun
- A Razorpay Test Mode account
- A Groq API key

### Backend environment

Create a `.env` file in the project root.

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b

RAZORPAY_KEY_ID=your_razorpay_test_key_id
RAZORPAY_KEY_SECRET=your_razorpay_test_key_secret
```

Do not commit `.env`.

### Install backend dependencies

```bash
uv sync
```

### Seed the catalog

```bash
uv run python -m scripts.seed_catalog
```

The seed process is designed to be idempotent.

### Start the backend

```bash
uv run uvicorn apps.api.main:app --reload
```

The backend is available on the local API server used by the frontend.

### Install frontend dependencies

```bash
cd frontend
bun install
```

### Start the frontend

```bash
bun dev
```

Open:

```text
http://localhost:3000
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes for live agent reasoning | Groq API key |
| `GROQ_MODEL` | Yes for live agent reasoning | Groq model name |
| `RAZORPAY_KEY_ID` | Yes for payment flow | Razorpay Test Mode key ID |
| `RAZORPAY_KEY_SECRET` | Yes for payment flow | Razorpay Test Mode secret |

The current project keeps provider-specific LLM behavior behind the LLM client boundary. The merchant agent should not depend on provider-specific API details.

## Razorpay Test Mode

To run the real payment flow:

1. Create or open a Razorpay Test Mode account.
2. Generate Test Mode API keys.
3. Put the key ID and key secret in `.env`.
4. Start the backend and frontend.
5. Select a supported payment scenario.
6. Complete the browser checkout with Razorpay Test Mode data.
7. Let the backend verify and reconcile the payment.

The retry flow does not reuse the failed Razorpay Order. Uplift creates a fresh Order for the retry.

For deployed webhook use, configure the Razorpay Test Mode webhook separately and store the webhook secret outside source control.

## API

The main application endpoints include:

```text
POST /api/purchases/prepare
POST /api/purchases/{session_id}/approve
POST /api/purchases/{session_id}/verify
POST /api/purchases/{session_id}/payment-failure
POST /api/purchases/{session_id}/retry

GET /api/overview
GET /api/transactions/{session_id}
GET /api/audit
GET /api/experiment/summary
```

The backend remains authoritative for all money-sensitive operations.

## Testing

Run the full backend test suite:

```bash
uv run pytest
```

Run frontend linting:

```bash
cd frontend
bun run lint
```

Run the production frontend build:

```bash
bun run build
```

The final validation should cover:

```text
successful upsell
no upsell
over budget
policy rejection
payment failure -> retry -> success
```

## Demo Walkthrough

A judge-friendly demo can follow this sequence:

```text
1. Buyer enters a natural-language request with a budget.
2. Merchant Agent interprets the request.
3. Backend searches the catalog.
4. Backend identifies valid upsell candidates.
5. Merchant Agent proposes at most one upsell.
6. Backend calculates the exact amount.
7. Merchant policy is checked.
8. Buyer sees the base product and the proposed upsell.
9. Buyer approves the exact amount.
10. Backend performs dual authorization.
11. Razorpay Checkout handles payment.
12. Backend verifies the payment.
13. Backend reconciles the transaction.
14. A failed payment can use one fresh retry Order.
15. Audit and measurement data are recorded.
16. The dashboard shows the transaction and audit state.
```

The visual story is:

```text
What the buyer wants
        |
        v
What the agent adds
        |
        v
Why it added it
        |
        v
What the exact total is
        |
        v
Why the money is safe
        |
        v
How payment is verified
```

## Measurement

Uplift includes an experiment summary endpoint with values such as:

- Sessions
- Successful orders
- Revenue
- Average order value
- Conversion
- Revenue per session
- AOV lift
- Upsell acceptance
- Blocked unsafe actions
- Payment recovery

### Measurement rule

Current measurement is an observational fallback.

The current grouping is based on whether a server-computed upsell is present:

```text
upsell present -> treatment
no upsell      -> control
```

This does not create a randomized experiment.

Do not describe the observed revenue difference as causal incremental revenue. The correct description is that the value is an observed difference in the current Test Mode dataset.

## Real vs Simulated

| Area | Status |
|---|---|
| Catalog data | Seeded demo data |
| Product relationships | Seeded merchant-defined data |
| AI reasoning | Live LLM integration when configured |
| Buyer approval | Real backend authorization flow |
| Razorpay order creation | Real Test Mode API |
| Razorpay checkout | Real Test Mode browser flow |
| Payment verification | Real server-side verification |
| Retry | Real Test Mode retry flow with a fresh Order |
| Audit records | Real application records |
| Experiment results | Measured Test Mode observations |
| Production payments | Not enabled |

## Security and Money Controls

Uplift treats the following as backend-only authority:

```text
price
policy
authorization
payment state
payment success
retry count
audit state
```

Important controls include:

- Integer paise for money.
- Server-side price calculation.
- Deterministic upsell relationships.
- Maximum one upsell per session.
- Maximum autonomous upsell item value of ₹1,000.
- Normal order limit of ₹5,000 before extra confirmation.
- Exact offer matching for buyer approval.
- Durable approval evidence.
- Maximum one payment retry.
- Fresh Razorpay Order for the retry.
- Server-side payment verification and reconciliation.
- Append-only audit logging.

## Known Limitations

This MVP is intentionally limited.

- Single merchant.
- Seeded gaming catalog with 30 products.
- Lightweight AI Buyer.
- Lightweight Merchant Agent.
- No concurrency testing.
- Small controlled measurement sample.
- Current experiment assignment is observational, not randomized.
- Upsell acceptance measurement requires final validation before use as a headline KPI.
- No production AI shopping platform integration.
- No ACP, AP2, x402, or UAP implementation.
- SQLite is intended for the demo. A production deployment should use a persistent production database and stronger operational controls.
- Razorpay Test Mode is used for the demo. Live payments are not part of this build.

## Design Principles

### Determinism is a security control

AI output can help select an action, but the backend must recompute and validate all money-sensitive values.

### Approval must match the exact offer

The buyer does not approve a general request. The buyer approves the exact server-computed offer.

### A retry is a new financial attempt

A failed Razorpay Order stays as the failed order. A retry uses a fresh Order.

### Browser state is not payment truth

The frontend callback is not sufficient to mark a payment as successful. The backend verifies and reconciles the payment.

### Auditability is part of the product

Important decisions must leave durable evidence.

### Do not fabricate measurement

Observed Test Mode metrics must not be presented as causal proof without a valid randomized experiment.

## Current Status

The core MVP implementation is complete and has been exercised end to end in Razorpay Test Mode.

Implemented areas include:

- Deterministic backend money layer.
- Structured 30-SKU catalog.
- Merchant Agent.
- AI Buyer.
- Dual authorization.
- Razorpay Test Mode checkout.
- Server-side verification and reconciliation.
- Bounded payment retry.
- Durable buyer approval evidence.
- Audit logging.
- Merchant dashboard and transaction views.
- Scenario Selector.
- Product and brand imagery.
- Experiment summary and measurement.
- Frontend hardening and regression work.

The remaining work is final review, targeted metric validation, UI polish where needed, regression checks, and final submission preparation.

## Production Path

A realistic production path would keep the same core architecture:

```text
AI reasoning
    |
    v
Validated structured contract
    |
    v
Deterministic backend
    |
    +--> pricing
    +--> policy
    +--> authorization
    +--> payment execution
    |
    v
Payment provider
```

Potential production upgrades include:

- PostgreSQL instead of SQLite.
- Real merchant authentication.
- Rate limiting.
- Secrets rotation.
- Stronger observability.
- Concurrency testing.
- Formal randomized experiment assignment.
- Production payment configuration.
- Public webhook endpoint with HTTPS.
- Real AI shopping platform integration.

## License

No project license is defined in the current project documentation.

Add a license before public distribution if the repository will be shared outside this project.
