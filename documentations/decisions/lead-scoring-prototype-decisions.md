# Lead Scoring Prototype Decisions

This document captures implementation-specific decisions for the working lead-scoring prototype.

These are intentionally separate from [decisions.md](/Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/decisions/decisions.md), which holds broader product and architecture decisions.

---

## 1. Rule Contracts Are Defined In Application Code In V1

- **Decision:** Scoring rule contracts are not stored in PostgreSQL in this prototype. They are defined in application code and resolved by `rule_type + version`.
- **Why:**
  - contracts are global and fixed for the prototype
  - validation logic is tightly coupled to contract shape
  - keeping them in code avoids building a second metadata persistence layer for reviewer-only scope
- **Current implementation:**
  - contract definitions live in [app/src/services/lead_scoring_rules/contracts/registry.py](/Users/shagunarora/work-in-progress/meraki-labs-assignment/app/src/services/lead_scoring_rules/contracts/registry.py)
  - tenants persist only rule instances in `lead_scoring_rules`
  - compatibility is carried by `rule_config.version`
- **Deferred from V1:** A database-backed contract registry only becomes useful if contracts must be managed dynamically without deploys.

---

## 2. Behavioral Event Catalog Is Mocked In Application Code In V1

- **Decision:** Behavioral scoring rule `rule_config.event_name` is validated against a code-defined mock PostHog event catalog.
- **Why:**
  - reviewers need deterministic allowed values
  - we do not want to add a real PostHog metadata integration in this prototype
  - the same source should drive both contract discovery and insert validation
- **Current implementation:**
  - mock event catalog lives in [app/src/integrations/posthog/event_catalog.py](/Users/shagunarora/work-in-progress/meraki-labs-assignment/app/src/integrations/posthog/event_catalog.py)
  - the behavioral contract exposes those values via [app/src/services/lead_scoring_rules/contracts/registry.py](/Users/shagunarora/work-in-progress/meraki-labs-assignment/app/src/services/lead_scoring_rules/contracts/registry.py)
  - API-level validation enforces the same list in [app/src/services/lead_scoring_rules/validations/behavior.py](/Users/shagunarora/work-in-progress/meraki-labs-assignment/app/src/services/lead_scoring_rules/validations/behavior.py)
- **Deferred from V1:** Real PostHog-backed event discovery.

---

## 3. Behavior Rule Property Filters Stay Open In V1

- **Decision:** `rule_config.property_filters` is accepted as an open JSON object in V1.
- **Why:**
  - event names were enough to constrain the prototype contract
  - modeling a mocked allowlist for event-property keys and values would add complexity without improving the reviewer flow materially
- **Current implementation:**
  - validation checks that `property_filters`, when provided, is an object
  - there is no allowlist of property names or value enums yet
- **Deferred from V1:** A PostHog-backed property catalog or a mocked property schema per event type.

---

## 4. Tenant Score Computation Runs Sequentially In V1

- **Decision:** Tenant lead score computation is executed sequentially in this prototype.
- **Why:**
  - reviewer-scale data is small
  - the implementation stays easier to reason about and debug
  - concurrency adds complexity without changing the demonstration value of the slice
- **Current implementation:**
  - one request computes all leads for one tenant
  - lead processing is synchronous and in-order
- **Deferred from V1:** Parallel lead computation.

---

## 5. Tenant Score Computation Uses One Database Transaction

- **Decision:** The tenant scoring compute flow persists all lead score updates inside one transaction.
- **Why:**
  - the reviewer should not see partially applied score updates for one tenant run
  - if computation fails midway, the tenant state should roll back cleanly
- **Current implementation:**
  - `POST /api/core/tenants/{tenant_id}/scoring/compute` opens one transaction
  - all score and stage writes for that request participate in the same transaction
- **Deferred from V1:** Partial progress tracking or resumable compute runs.

---

## 6. Scores Are Proportionally Normalized When Tenant Score Budget Exceeds 100

- **Decision:** If the sum of active positive tenant rule deltas exceeds `100`, final lead scores are proportionally normalized into the `0..100` range.
- **Why:**
  - this preserves relative ranking between leads
  - it avoids hard-clamping multiple distinct raw scores to `100`
  - it keeps rule configuration flexible for the prototype
- **Current implementation:**
  - raw score is computed additively from matched fit and behavior rules
  - positive active rule deltas define the tenant max possible score budget
  - if that budget exceeds `100`, final score is `round((raw_score / max_possible_score) * 100)` and then clamped into `0..100`
- **Deferred from V1:** A stricter rule-budget validation policy at rule creation/update time.
