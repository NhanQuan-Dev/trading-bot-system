## 0. Scope

This document applies to **every change**, including but not limited to:

- New feature implementation
- Feature modification
- Refactor (logic, structure, naming)
- Configuration / environment changes
- Performance optimizations
- Any behavior change, no matter how small

No exceptions.

---

## 1. Core Principles (MANDATORY)

### 1.1 No Assumptions

- The AI must **never assume system behavior**
- Every conclusion must be backed by at least one of:
    - Existing code
    - Explicit requirements or specs
    - Actual data (DB schema, logs, events)
    - Documented conventions

If no evidence exists → stop and request clarification.

---

### 1.2 No Guessing User Intent

- Do not infer what the user “probably wants”
- Do not invent hidden requirements
- If multiple reasonable interpretations exist → list all and ask

---

## 2. Mandatory Change Analysis Process

### 2.1 Change Classification

Before doing anything, clearly classify the change:

- 
- Behavioral change
- 
- Business logic change
- 
- Data / schema change
- 
- Performance-related change
- 
- UI / UX change
- 
- Infrastructure / configuration change

If unclear → do not proceed.

---

### 2.2 Impact Scan (Full Surface Area)

The AI **must explicitly review all layers below**:

- Inputs (API, UI, events, messages)
- Validation & sanitization
- Business logic
- Data layer (DB, cache, snapshots)
- Side effects (orders, positions, jobs, webhooks, notifications)
- State transitions (previous → next)
- Backward compatibility
- Realtime / async behavior
- Error handling & retry logic

No layer may be skipped based on assumptions.

---

### 2.3 Non-Happy-Path States

The AI must reason about:

- Missing or null data
- Partial / intermediate states
- Paused or interrupted flows
- Retries and duplicated events
- Re-runs with the same input
- Service restarts
- Race conditions
- Concurrent updates

Uncovered cases must be explicitly listed.

---

## 3. Reasoning Requirements

### 3.1 Every Claim Needs a Reason

For every conclusion, the AI must be able to answer:

- Why is this true?
- What evidence supports it?
- What breaks if this is wrong?

Forbidden phrases without proof:

- “Usually…”
- “Probably…”
- “Should be fine…”

---

### 3.2 Explicit Fact Separation

The AI must clearly label:

- **FACT** – verified by code or documentation
- **ASSUMPTION** – temporarily assumed
- **UNKNOWN** – insufficient information

Mixing these is not allowed.

---

## 4. Edge Cases & Future-Proofing

### 4.1 Beyond Happy Path

For every feature:

- What happens outside the normal flow?
- What if execution stops midway?
- What if the same action is replayed?
- What if old data meets new logic?

---

### 4.2 Do Not Lock the Future

The AI must check:

- Hard-coded values
- Tight coupling to a single strategy or flow
- Scalability limitations
- Extensibility constraints

---

## 5. Communication Rules

### 5.1 Stop When Uncertain

If any of the following occur:

- Ambiguous requirements
- Missing context
- Conflicting interpretations

→ Stop and ask. Never auto-decide.

---

### 5.2 Ask High-Value Questions

Questions must:

- Be precise
- Affect logic or correctness
- Remove assumptions

No filler questions.

---

## 6. Mandatory Output Structure

Every change review or implementation must include:

1. Change summary
2. Impacted components
3. Active assumptions
4. Checked edge cases
5. Missing or unclear information
6. Deployment risks
7. Suggested tests / verification steps

Missing any item = incomplete work.

---

## 7. Common Trivial Bugs to Actively Prevent

The AI **must proactively check and prevent** the following categories.

### 7.1 Syntax & Language Pitfalls

- Missing or mismatched brackets, quotes, parentheses
- Trailing commas (language-dependent)
- Wrong indentation (Python, YAML)
- Incorrect type annotations
- Shadowed variables
- Incorrect enum/string comparisons
- Boolean logic errors (AND vs OR)
- Floating-point precision assumptions

---

### 7.2 Data & Schema Mistakes

- Column renamed but not migrated
- Nullable field assumed non-null
- Default values silently changed
- Timezone mismatches (UTC vs local)
- Decimal vs float confusion
- ID type mismatch (UUID vs int)
- JSON schema drift

---

### 7.3 Logic & Flow Errors

- Off-by-one loops
- Incorrect boundary conditions
- State not updated atomically
- Partial updates without rollback
- Duplicate side effects on retry
- Missing idempotency guards
- Order of operations errors

---

### 7.4 Async & Realtime Bugs

- Await missing or misplaced
- Fire-and-forget tasks not tracked
- Race conditions on shared state
- Event handlers running out of order
- UI assuming synchronous updates
- Realtime updates not paused correctly

---

### 7.5 Configuration & Environment Errors

- Wrong env variable name
- Missing default config
- Different behavior between dev/staging/prod
- Feature flag checked in one place only
- Case-sensitive config mismatches
- Secrets assumed to exist

---

### 7.6 UI / Integration Issues

- UI updated without backend confirmation
- Loading state not reset on error
- Optimistic update without rollback
- API contract drift
- Breaking change without versioning

---

## 8. Final Rule (Non-Negotiable)

If something is:

- Not proven → do not assert
- Not clear → do not guess
- Not safe → do not implement

The AI exists to **reduce risk**, not to move fast blindly.

---

### 7.7 External Data & Normalization Checks (NEW)

- **Symbol Normalization:** Never assume exchange symbols match internal config. Always normalize (e.g., `ETH/USDT` -> `ETHUSDT`) before comparison.
- **External vs Internal Model Mapping:**
  - Verify DB Model definition (`models/*.py`) before assigning fields. Do not guess field names based on API response keys.
  - Required Fields Check: When creating new DB entities, explicitly list all `nullable=False` columns and ensure they are populated (e.g., `user_id`, `exchange_id`, `created_at`).

### 7.8 API Integration Verification (NEW)
- **Response Shape Verification:** Do not assume an API endpoint satisfies all data needs just by its name (e.g., `/account` vs `/positionRisk`). Read the docs or inspect actual response payloads first.
- **Data Completeness:** If an API is missing critical fields (like `markPrice`), look for alternative or complementary endpoints before writing partial data.