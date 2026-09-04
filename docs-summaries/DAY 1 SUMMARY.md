## Module 2 — Summary

### What we did

- Created the SQLite database configuration.
    
- Connected **SQLModel → SQLite**.
    
- Created all **7 core Uplift models**:
    
    - `Product`
        
    - `CompatibilityMap`
        
    - `BuyerProfile`
        
    - `Session`
        
    - `CartLineItem`
        
    - `PolicyConfig`
        
    - `AuditEvent`
        
- Connected database initialization to FastAPI using the modern **`lifespan`** pattern.
    
- Registered the models with SQLModel before creating tables.
    
- Successfully created all 7 SQLite tables.
    
- Verified them with SQLModel's database inspection.
    

### Mistakes / Issues

- **Mistake 1: Used deprecated `@app.on_event()`**
    
    - **Problem:** FastAPI flagged `on_event` as deprecated.
        
    - **Improvement:** Replaced it with the modern `lifespan` approach.
        
- **Mistake 2: Models weren't registered before `create_all()`**
    
    - **Problem:** Database inspection returned:
        
        ```text
        []
        ```
        
    - **Why:** SQLModel metadata didn't know about the models yet.
        
    - **Improvement:** Imported `apps.api.models` before calling `SQLModel.metadata.create_all()`.
        
- **Mistake 3: Initial dependency setup produced a compatibility warning**
    
    - **Problem:** `httpx`/Starlette produced a deprecation warning.
        
    - **Improvement:** We identified it as non-blocking and avoided unnecessary mid-module dependency changes.
        

### Final result

```text
7 tables created ✅
FastAPI working ✅
SQLite working ✅
SQLModel working ✅
Latest stable versions ✅
```

**Main lesson:** the database schema only becomes real when the models are actually registered with SQLModel's metadata.

**Break: 20 minutes.**

![[Pasted image 20260831024938.png]]

### Module 3 ✅

- Finalized **30 gaming SKUs** across 6 categories.
    
- Added **128 deterministic compatibility mappings**.
    
- Added the Genshin merchandise ecosystem and richer cross-sell relationships.
    
- Added `max_autonomous` protection for the **₹1,000 autonomous-upsell limit**.
    
- Created `scripts/seed_catalog.py` and `tests/unit/test_catalog.py`.
    
- Tests: **9 passed, 1 warning**.
    
- Database: **30 products, 128 mappings**.
    

### Mistakes / Fixes

- **Seed script import error:**  
    Running:
    
    ```powershell
    uv run python scripts/seed_catalog.py
    ```
    
    caused:
    
    ```text
    ModuleNotFoundError: No module named 'apps'
    ```
    
    because pytest's `pythonpath = ["."]` setting doesn't apply to normal Python execution.
    
- **Fix:**  
    Added:
    
    ```text
    scripts/__init__.py
    ```
    
    and ran the script as a module:
    
    ```powershell
    uv run python -m scripts.seed_catalog
    ```
    
    This fixed the import path cleanly without adding `sys.path` hacks.
    
- **Existing warning:** Starlette/httpx still shows a deprecation warning. Tests pass, so we left the dependency setup unchanged for now.
    

**Next:** Module 4 — `search_catalog`.
![[Pasted image 20260831214807.png]]

## Module 4 — Commerce Tools ✅

- Built `search_catalog`
    - deterministic search
    - ranking added
    - max 5 results
    - category hint supported
- Built `get_upsell_candidates`
    - reads only from `CompatibilityMap`
    - returns product + reason + `max_autonomous`
- Built `price_order`
    - authoritative DB pricing
    - quantity handling
    - inventory validation
    - deterministic breakdown
    - ignores caller-supplied prices
- Added unit tests for all three tools.

### Mistakes / Fixes

- **Search ranking test failed:** an exact-name match could outrank an explicitly requested category.
    - Fix: `category_hint` became a **hard filter**, while ranking is applied within that category.
- **Natural-language search was too strict:** requiring every query word to match caused `"gaming controller"` to return nothing for DualSense because `"gaming"` wasn't present.
    - Fix: changed matching from `all(...)` to `any(...)`, with ranking deciding relevance.
- We kept the existing **Starlette/httpx deprecation warning** because it doesn't break tests and dependency churn wasn't justified yet.
![[Pasted image 20260831223303.png]]

### Module 5 ✅

- Implemented deterministic `check_policy()` as the **merchant policy gate**.
    
- Added **buyer budget** enforcement.
    
- Added **maximum 1 upsell per session** enforcement.
    
- Added the **₹1,000 autonomous-upsell item limit**.
    
- Added the **₹5,000 autonomous order-total limit**.
    
- Added **allowed-product** enforcement using `allowed_product_ids`.
    
- Implemented the three policy decisions:
    
    - `ALLOWED`
        
    - `REQUIRES_CONFIRMATION`
        
    - `REJECTED`
        
- Added **policy version propagation** through `PolicyResult`.
    
- Created `apps/api/policy/__init__.py` and `apps/api/policy/engine.py`.
    
- Created `tests/unit/test_policy.py` with **7 policy tests**.
    
- Full project regression suite: **36 passed**.
    
- Policy remains completely **deterministic and outside the LLM**.
    

### Mistakes / Fixes

- **Initial Policy Engine import error:**  
    Running:
    
    ```powershell
    uv run pytest tests/unit/test_policy.py
    ```
    
    caused:
    
    ```text
    ModuleNotFoundError: No module named 'apps.api.policy.engine'
    ```
    
    because the Policy Engine package/file had not yet been created.
    
- **Fix:**  
    Added:
    
    ```text
    apps/api/policy/
    ├── __init__.py
    └── engine.py
    ```
    
    This allowed pytest to collect the test correctly.
    
- **Incremental TDD implementation:**  
    The policy rules were implemented one at a time:
    
    ```text
    buyer budget
    → upsell count
    → autonomous upsell price
    → autonomous order total
    → allowed products
    → policy version
    ```
    
    Each rule was first tested and then implemented.
    
- **Policy semantics clarified:**
    
    ```text
    Buyer exceeds budget
    → REJECTED
    
    Too many upsells
    → REJECTED
    
    Upsell exceeds autonomous price limit
    → REQUIRES_CONFIRMATION
    
    Order exceeds autonomous total
    → REQUIRES_CONFIRMATION
    
    Otherwise
    → ALLOWED
    ```
    
- **Existing warning:** Starlette/httpx still shows a deprecation warning. Tests pass, so we left the dependency setup unchanged for now.
    
![[Pasted image 20260831231139.png]]

## Module 6 — Audit + Day 1 Verification ✅

- Built `record_audit_event`
    
    - persists `AuditEvent` records to SQLite
        
    - stores decision, reason, actor, action, session, and policy version
        
    - serializes structured data into `payload_json`
        
- Verified **append-only audit behavior**
    
    - each event creates a separate record
        
    - existing audit events remain unchanged
        
- Added audit payload serialization tests.
    
- Built the Day 1 integration test covering:
    
    - `search_catalog`
        
    - `get_upsell_candidates`
        
    - `price_order`
        
    - `check_policy`
        
    - `record_audit_event`
        
- Updated the integration flow to use **authoritative `price_order()` pricing** instead of manually calculating totals.
    
- Finalized a realistic Genshin happy-path scenario using the **₹899 autonomous-eligible Vision Keychain**.
    
- Ran the complete regression suite: **40 tests passed**.
    
- **Day 1 is now complete.** The PRD defines this deterministic catalog → upsell → pricing → policy → audit path as the Day 1 acceptance flow.
    

### Mistakes / Fixes

- **Audit service import error:** `apps.api.audit.service` did not exist when the first test was created.
    
    - Fix: created:
        
    
    ```text
    apps/api/audit/
    ├── __init__.py
    └── service.py
    ```
    
- **Unrealistic GTA V test scenario:** the first integration test selected the deterministic `GTA V → PS5` candidate, creating an approximately ₹57,489 basket.
    
    - Fix: changed the happy path to the Genshin ecosystem and selected `MER-002` (₹899), which is explicitly the principal `max_autonomous=True` example.
        
- **Integration test manually calculated the basket total:** this bypassed the intended authoritative pricing boundary.
    
    - Fix: changed the test to call `price_order()` so the amount comes from current database prices.
        
- **Existing Starlette/httpx deprecation warning:** still present but does not fail tests.
    
    - Fix: left the dependency state unchanged for now to avoid unnecessary dependency churn.

![[Pasted image 20260901012620.png]]