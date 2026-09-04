## Day 3 — Module 1: Groq LLM Client ✅

### Summary

Completed the first Merchant Agent foundation:

```
Uplift
  ↓
Merchant Agent
  ↓
LLMClient
  ↓
Groq API
  ↓
openai/gpt-oss-20b
```

Implemented:

- Groq SDK integration
- `LLMClient` abstraction
- `GROQ_API_KEY` configuration
- `GROQ_MODEL` configuration
- explicit configuration override support
- validation when API key/model configuration is missing
- offline unit tests for the client boundary
- full regression testing

The client is intentionally only an **LLM boundary**. It does not receive authority over pricing, policy, authorization, or Razorpay. That preserves the core Uplift architecture.

### Mistakes / Issues

**1. We initially started with OpenAI.**

The first implementation plan used the OpenAI SDK before you clarified that you didn't have API credits.

We corrected this before actually building the integration and switched to:

```
Groq
+
gpt-oss-20b
```

This is better aligned with your zero-cost/free-tier requirement.

**2. Provider choice could have been hard-coded.**

Instead, we deliberately created an `LLMClient` abstraction so the provider can be changed later without rewriting the Merchant Agent.

**3. We avoided real API calls during the module.**

That was intentional. Module 1 tests configuration locally rather than consuming free-tier requests. External API behavior belongs in integration testing.

### Engineering lesson

The LLM should be treated as a **replaceable reasoning component**, not the core business authority.

```
LLM → proposes/evaluates
Backend → decides/authorizes/charges
```

That remains one of the project's non-negotiable rules.
![[Pasted image 20260903203151.png]]

## Day 3 — Module 2: Structured Agent Contracts ✅

### Summary

We successfully added and tested the three core agent contracts:

```
PurchaseRequest
      ↓
MerchantAgentProposal
      ↓
UpsellProposal
```

The module enforces:

- non-empty purchase queries
- non-negative budgets
- optional buyer preferences
- valid product IDs
- non-empty upsell reasoning
- **at most one upsell**
- no price/policy/payment fields inside the LLM contract

Your results:

```
Module tests:    10 passed ✅
Full regression: 106 passed ✅
```

So the existing Day 1 + Day 2 functionality remains intact while adding the Merchant Agent schema layer.

This matches the project requirement for structured outputs and strict validation before agent output can affect the commerce flow.

## Mistakes / Issues

### 1. Expected test count was off

I initially said to expect **9 passed**, but you got:

```
10 passed
```

That's because the final test set contains 10 tests. This is **my counting mistake in the expected output**, not a code problem.

### 2. No implementation failure

The important result is:

```
106 passed
```

No regression was introduced.

### Engineering lesson

The LLM should produce **structured intent/proposals**, but those structures must remain limited to what the agent is actually allowed to decide.

```
LLM
 ↓
validated schema
 ↓
deterministic backend
 ↓
price / policy / authorization / payment
```

That separation is central to Uplift.
![[Pasted image 20260903204341.png]]

## Day 3 — Module 3: Agent Tool Contracts ✅

### Summary

We added typed contracts around the existing deterministic commerce tools:

```
search_catalog
get_upsell_candidates
price_order
```

The schemas enforce things like:

- valid/non-empty queries
- maximum 5 catalog results
- valid product IDs
- non-negative paise
- positive quantities
- non-empty line items
- structured pricing breakdowns

Most importantly, the LLM still **does not become the source of price or compatibility truth**. The contracts sit between agent reasoning and the deterministic backend.

Your previous full-suite baseline was **106 passed**, and this module was designed to preserve that regression safety.

### Mistakes / Issues

There was no implementation problem reported in this module.

One thing to keep in mind: I initially mixed up the expected test count in Module 2, but that was only my counting mistake; your actual test suite correctly reported **10 passed**.

### Engineering lesson

A tool contract is a **security boundary**, not just a type definition.

```
LLM output
    ↓
validated contract
    ↓
deterministic tool
    ↓
trusted backend result
```

That fits the PRD's requirement that the Merchant Agent use typed tools while remaining unable to invent products, compatibility, or prices
![[Pasted image 20260903205138.png]]

## Day 3 — Module 4 Summary ✅

We implemented the **actual Merchant Agent orchestration**.

The module now connects the components built in Modules 1–3:

```
PurchaseRequest
      ↓
search_catalog()
      ↓
LLM proposal
      ↓
validate base product
      ↓
get_upsell_candidates()
      ↓
validate upsell
      ↓
price_order()
      ↓
check_policy()
      ↓
PurchaseOffer
```

The Merchant Agent can now resolve a buyer request, select a catalog product, choose at most one valid upsell, and produce a structured offer. The deterministic catalog, pricing, and policy layers remain authoritative.

We also added the missing `PurchaseOffer` contract and extended the Groq client with structured-generation support so the agent receives schema-validated LLM output. Your original schemas already defined `PurchaseRequest`, `UpsellProposal`, and `MerchantAgentProposal`.

Your existing `price_order()` continues to derive prices directly from the database, including inventory checks, rather than trusting the agent.

### Tests

You confirmed:

```
Module 4 tests        ✅ ALL PASSED
Full regression       ✅ ALL PASSED
```

So **Day 3 Modules 1–4 are now complete.**

---

## Mistakes / Issues

### 1. We initially lacked the actual LLM request method

The existing `LLMClient` only initialized the Groq client and configuration; it did not yet have a structured-generation method.

**Fix:** Added structured generation to the client instead of putting Groq-specific API logic directly inside the Merchant Agent.

### 2. We had to be careful not to treat LLM output as truth

The biggest architectural risk was allowing the model to effectively decide:

```
price
compatibility
policy
```

**Fix:** The agent's output is only a proposal. Product validity, compatibility, pricing, and policy are checked independently by deterministic code.

### 3. Re-prompting needed a hard boundary

A malformed or invalid proposal cannot cause unlimited LLM calls.

**Fix:**

```
MAX_REPROMPTS = 1
```

This matches the project's bounded-agent requirement.

### 4. We had to avoid inventing compatibility

The model cannot simply say:

> "This accessory seems compatible."

**Fix:** the proposed upsell must exist in the deterministic result of `get_upsell_candidates()`. Your tool itself only returns relationships from `CompatibilityMap`.

### 5. Test count was not something to invent

CTD-4 explicitly warned not to fabricate the Module 3 test count. We kept that discipline rather than making up numbers.

---

## Engineering Lesson

The central lesson from Module 4 is:

> **An agent should coordinate trusted capabilities, not become a trusted capability itself.**

In Uplift:

```
LLM            → proposes
Pydantic       → validates structure
Catalog tools  → validate commerce facts
price_order    → owns money
Policy Engine  → owns policy
Razorpay       → remains outside the agent
```

That separation is one of the strongest parts of the architecture.