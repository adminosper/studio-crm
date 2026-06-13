## Lead Scoring And Qualification Implementation Plan

This document defines the exact implementation slice we will build for the Meraki work trial under `PS 1 — Venture-Studio CRM`.

The goal is not to build the whole CRM. The goal is to build one defensible, runnable, reviewer-friendly backend slice that demonstrates:

- tenant-scoped data modeling
- configurable scoring rules
- behavioral + fit scoring
- qualification stage transitions
- explicit assumptions and deferrals
- a clean API-only demo path

This plan is intentionally narrower than the full V1 product described in the assignment and the broader design documents.

---

## 1. Selected Slice

We will implement **Lead Scoring and Qualification** as a REST API only system using:

- `FastAPI`
- `PostgreSQL`
- `Docker Compose` with exactly two services:
  - `postgres`
  - `backend`

We will not build UI, background workers, or external integrations in this slice.

The reviewer should be able to:

1. inspect seeded tenants and leads
2. configure tenant-specific scoring rules
3. insert mock behavioral events
4. manually trigger score recomputation for a tenant
5. inspect lead scores and qualification stages before and after recomputation

---

## 2. Scope Boundary

### In Scope

- Multi-tenant lead scoring using tenant-scoped tables
- Lead fit scoring based on static lead attributes
- Lead behavioral scoring based on stored mock event data
- Tenant-configurable score thresholds:
  - `mql_score_threshold`
  - `sql_score_threshold`
- Rule CRUD for scoring rules
- Manual API-triggered recomputation for:
  - all active leads of a tenant
  - one specific lead in a tenant
- Lead stage transitions:
  - `pre_mql`
  - `mql`
  - `sql`
- Manual stage override support
- Reviewer helper APIs for mock data creation
- Seed data for at least two tenants to demonstrate isolation
- Clear README/API demonstration flow

### Out of Scope For This Implementation

- Real PostHog integration
- Webhook ingestion from external systems
- Async cron-based recomputation
- Message queues
- Outbound automation reactions to stage changes
- Studio-level rolled-up scoring defaults
- Authentication and full RBAC implementation
- Accounts, Contacts, Deals, and lead conversion flows
- UI

---

## 3. Demonstration Goal

The demo should prove four things clearly:

1. **Isolation**
   A tenant can only affect and query its own scoring configuration, leads, and events through tenant-scoped APIs.

2. **Configurability**
   Different tenants can have different fit rules, behavior rules, and qualification thresholds.

3. **Deterministic qualification**
   Given lead attributes and event history, recomputation produces a predictable score and stage.

4. **Reviewer usability**
   The reviewer can create leads, create events, run recomputation, and inspect results without writing SQL manually.

---

## 4. Exact Functional Slice

### 4.1 Lead Lifecycle Model In This Slice

Each lead will have:

- operational `status`
  - `active`
  - `disqualified`
  - `converted`
- qualification `stage`
  - `pre_mql`
  - `mql`
  - `sql`
- numeric `score`
- `score_last_updated_at`
- `is_stage_manually_overridden`

Recompute rules:

- only leads with `status = active` are scored
- score is recomputed every invocation
- stage is derived from thresholds unless `is_stage_manually_overridden = true`
- manually overridden leads still get a fresh score, but stage remains unchanged

### 4.2 Supported Rule Types

We will support two rule types.

#### Fit Rules

Rules based on lead attributes already stored in the database.

Detailed contract and compatibility rules live in [lead-scoring-rule-contracts.md](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/lead-scoring-rule-contracts.md).

Allowed lead fields:

- `industry`
- `company_size`
- `geography`
- `title`
- `source`

Supported operators:

- `equals`
- `not_equals`
- `in`
- `not_in`
- `gte`
- `lte`
- `contains`

#### Behavior Rules

Rules based on mock event aggregates for a lead.

Detailed contract and compatibility rules live in [lead-scoring-rule-contracts.md](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/lead-scoring-rule-contracts.md).

Supported event aggregate logic:

- event name match
- optional lookback window in days
- optional event property filters
- aggregate operators:
  - `count_gte`
  - `count_eq`

Example:

- `pricing_page_viewed count_gte 2 within 30 days => +20`

### 4.3 Threshold-Based Qualification

Each tenant will own:

- `mql_score_threshold`
- `sql_score_threshold`

Stage mapping:

- `score < mql_score_threshold` => `pre_mql`
- `score >= mql_score_threshold` and `< sql_score_threshold` => `mql`
- `score >= sql_score_threshold` => `sql`

### 4.4 Manual Recompute API

We will expose:

- recompute all active leads for one tenant
- recompute one lead for one tenant

The API response should summarize:

- how many leads were processed
- how many were skipped
- how many stage transitions occurred
- per-lead score deltas and resulting stages

---

## 5. Database Entities Required

We will keep the schema minimal and focused on this slice.

### 5.1 Core Entities

#### `tenants`

Required fields:

- `id`
- `name`
- `mql_score_threshold`
- `sql_score_threshold`
- `created_at`
- `deleted_at`

Reason:
Owns tenant-level scoring thresholds and isolates data.

#### `leads`

Required fields:

- `id`
- `tenant_id`
- `name`
- `email`
- `company`
- `industry`
- `company_size`
- `geography`
- `phone`
- `title`
- `source`
- `status`
- `stage`
- `score`
- `score_last_updated_at`
- `is_stage_manually_overridden`
- `created_at`
- `updated_at`

Reason:
Primary subject of the scoring engine.

#### `lead_scoring_rules`

Required fields:

- `id`
- `tenant_id`
- `rule_name`
- `rule_type`
- `score_delta`
- `is_active`
- `rule_config` as JSONB
- `created_at`
- `updated_at`

Reason:
Allows tenant-specific fit and behavior rule configuration in a single table.

#### `lead_events`

Required fields:

- `id`
- `tenant_id`
- `lead_id`
- `event_name`
- `event_properties` as JSONB
- `occurred_at`
- `created_at`

Reason:
This is the local mock replacement for PostHog event history.

### 5.2 Tenant ID Policy For This Slice

We will keep `tenant_id` on every tenant-scoped table in this implementation:

- `leads`
- `lead_scoring_rules`
- `lead_events`

Why we are keeping it:

- it keeps tenant scoping explicit in every query path
- it aligns with the broader multi-tenant design already documented for the CRM
- it keeps future RLS adoption straightforward
- it allows direct tenant filtering without relying only on joins through `lead_id`

So for this slice, yes, tenant-scoped tables should carry `tenant_id` directly.

### 5.3 Explicit Non-Entities For This Slice

We will not implement these now:

- `users`
- `accounts`
- `contacts`
- `deals`
- `lead_trigger_rules`
- `ai_prompt_configurations`
- outbound sequence tables
- `lead_score_runs`

Those belong to the full CRM, not to this focused implementation.

---

## 6. Seed Data Plan

The first-time seed should create enough data to demonstrate both isolation and scoring outcomes immediately after startup.

### 6.1 Tenants

Seed at least two tenants:

- `Acme SaaS`
- `Beta Fintech`

Each tenant should have different thresholds so the reviewer can see tenant-specific qualification behavior.

Example:

- `Acme SaaS`
  - `mql_score_threshold = 40`
  - `sql_score_threshold = 70`
- `Beta Fintech`
  - `mql_score_threshold = 50`
  - `sql_score_threshold = 80`

### 6.2 Leads

Seed 3 to 5 leads per tenant with different combinations of:

- industry
- company size
- geography
- title
- source
- status

At least one lead per tenant should cover each case:

- likely `pre_mql`
- likely `mql`
- likely `sql`
- skipped because `disqualified`
- stage-override case

### 6.3 Scoring Rules

Seed a small but meaningful rule set per tenant.

For example:

- fit rule: `industry in ['SaaS', 'FinTech'] => +20`
- fit rule: `company_size >= 200 => +15`
- fit rule: `title contains 'Founder' => +10`
- behavior rule: `pricing_page_viewed count_gte 2 in 30 days => +20`
- behavior rule: `demo_requested count_gte 1 in 30 days => +30`

Tenants should not share the exact same rule set. At least one rule or threshold should differ.

### 6.4 Events

Seed a few events per lead so recomputation produces non-trivial results immediately.

Examples:

- `page_viewed`
- `pricing_page_viewed`
- `demo_requested`
- `case_study_downloaded`

At least one lead should have:

- no events
- enough events to become `mql`
- enough events to become `sql`

### 6.5 Recommended Seed Outcome

After boot, the reviewer should be able to run one recompute call and observe:

- a lead staying `pre_mql`
- a lead becoming `mql`
- a lead becoming `sql`
- a lead being skipped due to `disqualified`
- a lead keeping stage unchanged because of manual override

---

## 7. What We Will Mock

### 7.1 Mocked Instead Of Real PostHog

We will not call PostHog or ingest real external event streams.

Instead we will mimic PostHog with `lead_events` rows inserted via:

- seed data
- reviewer helper APIs

Why this is acceptable for this slice:

- the feature being demonstrated is the scoring and qualification engine, not the external analytics integration
- local event storage gives deterministic behavior for demo and tests
- it keeps the build constrained to two Docker services

### 7.2 Mocked Tenant Context

We will not build full authentication.

Tenant context will be passed explicitly in the API path or request body, for example:

- `/api/core/tenants/{tenant_id}/...`

Why:

- reviewer clarity
- reduced setup complexity
- avoids spending the slice on auth rather than scoring

### 7.3 Mocked Scheduling

We will not implement cron or background jobs.

Recomputation will be triggered manually by API.

Why:

- the assignment only requires one working module
- manual execution is easier for reviewers
- logic stays testable and deterministic

---

## 8. Reviewer Helper APIs

We will explicitly split APIs into:

- `core` APIs
- `helper` APIs

Helper APIs exist only to make the demo easy. They are not product APIs.

### 8.1 Helper APIs We Should Provide

#### Tenant Inspection

- `GET /api/helpers/tenants`
- `GET /api/helpers/tenants/{tenant_id}/snapshot`

Purpose:
Show seeded thresholds, rule counts, lead counts, and recent events.

#### Lead Creation

- `POST /api/helpers/tenants/{tenant_id}/leads`

Purpose:
Insert a mock lead quickly for testing fit rules.

#### Event Creation

- `POST /api/helpers/tenants/{tenant_id}/leads/{lead_id}/events`
- `POST /api/helpers/tenants/{tenant_id}/events/bulk`

Purpose:
Inject behavioral activity for one lead or a batch of leads.

#### Random Mock Data Generation

- `POST /api/helpers/tenants/{tenant_id}/mock-data/leads`
- `POST /api/helpers/tenants/{tenant_id}/mock-data/events`

Purpose:
Generate sample data for reviewers without hand-crafting JSON.

#### Reset Or Re-seed For Demo

- `POST /api/helpers/reset-demo-data`

Purpose:
Restore the database to the known seeded demo state.

This endpoint is demo-only and should be clearly labeled as such.

---

## 9. Core APIs

These are the actual APIs that demonstrate the slice.

### 9.1 Lead Read APIs

- `GET /api/core/tenants/{tenant_id}/leads`
- `GET /api/core/tenants/{tenant_id}/leads/{lead_id}`

Should include:

- score
- stage
- status
- manual override flag

### 9.2 Threshold Configuration APIs

- `GET /api/core/tenants/{tenant_id}/scoring-thresholds`
- `PUT /api/core/tenants/{tenant_id}/scoring-thresholds`

Purpose:
Allow tenant-specific qualification tuning.

### 9.3 Rule Configuration APIs

- `GET /api/core/tenants/{tenant_id}/scoring-rules`
- `POST /api/core/tenants/{tenant_id}/scoring-rules`
- `PUT /api/core/tenants/{tenant_id}/scoring-rules/{rule_id}`
- `DELETE /api/core/tenants/{tenant_id}/scoring-rules/{rule_id}`

Contract discovery APIs:

- `GET /api/core/scoring-rule-contracts`
- `GET /api/core/scoring-rule-contracts/{rule_type}`

Validation expectations:

- rule type must be valid
- rule config shape must match rule type
- score delta must be integer
- inactive rules must be ignored by recomputation

### 9.4 Manual Override APIs

- `POST /api/core/tenants/{tenant_id}/leads/{lead_id}/manual-stage-override`
- `DELETE /api/core/tenants/{tenant_id}/leads/{lead_id}/manual-stage-override`

Purpose:
Demonstrate the rule that scoring updates score but does not overwrite a manually locked stage.

### 9.5 Recompute APIs

- `POST /api/core/tenants/{tenant_id}/scoring/recompute`
- `POST /api/core/tenants/{tenant_id}/leads/{lead_id}/scoring/recompute`

Response should expose:

- previous score
- new score
- previous stage
- new stage
- skip reason if any
- matched rules summary

### 9.6 Optional Run History APIs

- `GET /api/core/tenants/{tenant_id}/score-runs`
- `GET /api/core/tenants/{tenant_id}/score-runs/{run_id}`

These are optional, but strongly useful for reviewer clarity.

---

## 10. Core Services To Implement

The implementation should stay modular and align with `AGENTS.md`.

### 10.1 Services

- `LeadScoringRuleValidationService`
- `LeadBehaviorAggregationService`
- `LeadFitScoringService`
- `LeadBehaviorScoringService`
- `LeadQualificationService`
- `LeadScoreRecomputeService`

### 10.2 Repositories

- `TenantRepository`
- `LeadRepository`
- `LeadScoringRuleRepository`
- `LeadEventRepository`
- `LeadScoreRunRepository` if run logging is implemented

### 10.3 Utility Modules

- rule config schema helpers
- event property matching helpers
- score summary formatter
- mock data factory helpers

### 10.4 Lead Scoring Rule Feature Folder

Lead-scoring-rule-specific logic should live together under one feature area instead of being scattered.

Recommended structure:

- `src/services/lead_scoring_rules/service.py`
- `src/services/lead_scoring_rules/contracts/registry.py`
- `src/services/lead_scoring_rules/contracts/service.py`
- `src/services/lead_scoring_rules/contracts/types.py`
- `src/services/lead_scoring_rules/validations/base.py`
- `src/services/lead_scoring_rules/validations/fit.py`
- `src/services/lead_scoring_rules/validations/behavior.py`
- `src/services/lead_scoring_rules/validations/helpers.py`
- `src/services/lead_scoring_rules/validations/service.py`
- `src/services/lead_scoring_rules/normalization/rule_config.py`

Purpose of each:

- `service.py`
  Owns tenant-scoped rule CRUD orchestration and delegates validation/normalization.
- `contracts/registry.py`
  Holds the versioned rule-contract registry used by both APIs and validators.
- `contracts/service.py`
  Exposes contract discovery for non-tenant core APIs.
- `contracts/types.py`
  Holds typed structures used by contract resolution and validation.
- `validations/base.py`
  Defines the common validator interface for future shared pre-checks.
- `validations/fit.py`
  Validates fit-rule config against a specific contract version.
- `validations/behavior.py`
  Validates behavior-rule config against a specific contract version.
- `validations/helpers.py`
  Contains shared validation helpers used across rule validators.
- `validations/service.py`
  Resolves contracts by version and dispatches validation.
- `normalization/rule_config.py`
  Converts accepted or legacy configs into one canonical stored representation.

---

## 11. Scoring Engine Behavior

### 11.1 Recompute Flow

For each lead in scope:

1. verify the lead belongs to the tenant
2. skip if lead status is not `active`
3. load active fit rules for tenant
4. load active behavior rules for tenant
5. compute total fit score contribution
6. compute total behavior score contribution from `lead_events`
7. sum total score
8. optionally clamp score to a max value if we choose to enforce a hard ceiling
9. derive stage from tenant thresholds unless manual override exists
10. persist score and stage updates atomically
11. record run summary

### 11.2 Scoring Engine Design For This Slice

The scoring engine should stay deliberately simple and deterministic for this assignment.

Recommended design:

- one manual recompute endpoint for one tenant only
- one synchronous scoring pass
- additive scoring
- final score capped at `100`
- no queue
- no background worker
- no parallelization

Why no parallelization:

- expected scale in this slice is small
- manual recompute for ~100 leads is acceptable
- concurrency adds complexity without improving the quality of the assignment answer
- correctness and debuggability matter more than micro-optimization here

### 11.3 Mock Aggregation Strategy

Behavior aggregation is mocked in this slice because real aggregation would normally come from PostHog.

Recommended mocking strategy:

- keep only the raw `lead_events` table
- do not add a second aggregated mock table
- load relevant tenant events once
- aggregate in memory for the recompute run

Why this is preferred:

- avoids maintaining consistency between raw and aggregated mock tables
- reduces schema complexity
- is easier for a reviewer to understand
- is sufficient at this scale

### 11.4 Behavior Aggregation Execution Model

The engine should avoid a query pattern like:

- `number_of_leads * number_of_behavior_rules * query_per_combination`

Instead it should use a bulk execution model:

1. load all active leads for the tenant
2. load all active behavior rules for the tenant
3. derive the maximum required lookback window across behavior rules
4. load all tenant events within that outer window in one fetch
5. group events in memory by `lead_id`
6. evaluate each behavior rule against each lead's already-loaded event list

This keeps the implementation simple while avoiding obvious inefficiency.

### 11.5 Mock Aggregation Service Structure

Recommended feature-area files:

- `src/services/lead_scoring_engine/service.py`
- `src/services/lead_scoring_engine/fit_scorer.py`
- `src/services/lead_scoring_engine/behavior_scorer.py`
- `src/services/lead_scoring_engine/behavior_aggregator.py`
- `src/services/lead_scoring_engine/qualification.py`
- `src/services/lead_scoring_engine/types.py`

Purpose of each:

- `service.py`
  Orchestrates tenant recompute end to end.
- `fit_scorer.py`
  Evaluates validated fit rules against one lead.
- `behavior_scorer.py`
  Applies behavior rules against pre-aggregated lead activity.
- `behavior_aggregator.py`
  Loads tenant events once and prepares in-memory lead-level event collections.
- `qualification.py`
  Maps final score to `pre_mql`, `mql`, or `sql`.
- `types.py`
  Holds typed structures for recompute summaries and per-lead results.

### 11.6 Manual Recompute Endpoint Scope

For now, only one endpoint is required:

- `POST /api/core/tenants/{tenant_id}/scoring/recompute`

The single-lead recompute endpoint can remain deferred unless we explicitly need it later.

### 11.7 Tenant Recompute Response Shape

The recompute response should summarize:

- `tenant_id`
- `processed_lead_count`
- `skipped_lead_count`
- `stage_transition_count`
- `results`

Each per-lead result should include:

- `lead_id`
- `previous_score`
- `new_score`
- `previous_stage`
- `new_stage`
- `status`
- `skip_reason` when applicable
- `matched_fit_rules`
- `matched_behavior_rules`

### 11.8 Lead Skip Rules

The scoring engine should skip:

- `status = disqualified`
- `status = converted`

If a lead is skipped:

- score remains unchanged
- stage remains unchanged
- response should explain the skip reason

### 11.9 Manual Stage Override Behavior

If `is_stage_manually_overridden = true`:

- recompute the score normally
- update `score`
- update `score_last_updated_at`
- do not change `stage`

This should be explicit in both implementation and tests.

### 11.2 Recommended Simplifications

To keep the slice sharp, we should adopt these simplifications:

- additive scoring only
- no nested boolean logic
- no negative event windows beyond a simple lookback days filter
- no cross-lead or cross-account behavior inference
- event-to-lead association is direct through `lead_id`, not resolved by email matching

This differs from the full V1 design, but it is much better for a clean implementation slice.

---

## 12. Assumptions

These assumptions should be explicit in the plan and README.

### Product Assumptions

- This slice demonstrates tenant-specific scoring logic, not the whole CRM.
- Behavioral events are already resolved to a specific lead.
- Email identity stitching is outside this implementation.
- Score recomputation is manual for demo purposes.

### Technical Assumptions

- PostgreSQL is the only persistence layer.
- A local `lead_events` table is sufficient to mimic external analytics.
- API consumers pass tenant scope explicitly.
- We do not need auth to demonstrate business logic correctness.

---

## 13. Deferred From Full V1 Due To Time Constraints

These items may exist in the real V1 or broader system design, but we will defer them from the current implementation.

### Real V1 Capabilities Deferred

- PostHog API integration and HogQL queries
- webhook ingestion and signature validation
- cron-based periodic scoring
- queue-based async recomputation
- production observability and tracing
- role-based authorization
- full RLS enforcement setup
- lead trigger rules for automatic lead creation
- outbound enrollment actions on stage transition
- audit trails for stage transition jobs
- studio-level default scoring rules

### Broader CRM Features Deferred

- tenant onboarding flows
- account/contact/deal creation
- lead conversion to deal pipeline
- rolled-up parent workspace dashboards
- performance marketing attribution dashboards
- AI outbound flows

---

## 14. First Implementation Milestones

This is the recommended execution order when we start coding.

### Milestone 1

- bootstrap FastAPI project
- docker compose with postgres + backend
- config module
- schema creation and seed flow

### Milestone 2

- lead, tenant, rule, and event data models
- repositories
- list/read APIs for seeded data

### Milestone 3

Rule-contract and scoring-engine work should be split into smaller subtasks:

1. Add rule contract discovery endpoints under `/api/core/scoring-rule-contracts`.
2. Introduce a central versioned contract registry for `fit` and `behavior` rules.
3. Add `version` inside `rule_config` for both seed data and API-created rules.
4. Add `BaseScoringRuleValidator` as the common validator interface.
5. Add `FitScoringRuleValidator` for fit-rule version-specific validation.
6. Add `BehaviorScoringRuleValidator` for behavior-rule version-specific validation.
7. Add `LeadScoringRuleValidationService` to resolve `rule_type + version`, dispatch the correct validator, and return canonical config.
8. Tighten rule insertion and rule update flows so DB writes happen only after semantic validation.
9. Add canonical normalization rules, especially for optional objects such as `property_filters`.
10. Build the fit scoring engine.
11. Build the behavior scoring engine.
12. Build the qualification stage mapping engine.

### Milestone 4

Scoring-engine and manual recompute work should be split into smaller subtasks:

1. Add `lead_scoring_engine` feature folder and typed recompute result structures.
2. Add fit scorer for validated fit rules.
3. Add mock behavior aggregator that bulk-loads tenant events once for the recompute run.
4. Add behavior scorer on top of the in-memory aggregated event collections.
5. Add qualification service for threshold-based stage mapping.
6. Add tenant recompute orchestration service.
7. Add `POST /api/core/tenants/{tenant_id}/scoring/recompute`.
8. Add skip handling for `disqualified` and `converted` leads.
9. Add manual-stage-override protection during recompute.
10. Add tests for score cap, skip behavior, stage transitions, and behavior window filtering.

### Milestone 5

- helper APIs for reviewers
- reset/reseed flow
- README demo walkthrough
- tests

---

## 15. Reviewer Demo Script

The final README should guide the reviewer through a short flow like this:

1. start the stack with docker compose
2. inspect seeded tenants
3. inspect seeded leads for tenant A
4. inspect seeded scoring rules for tenant A
5. insert new mock events for one lead
6. run tenant recompute
7. verify score and stage changed
8. set manual stage override
9. add more events and rerun recompute
10. verify score changes but stage remains locked
11. repeat for tenant B to show isolation and different thresholds

---

## 16. Success Criteria

This slice is successful if:

- the reviewer can run it from scratch with two services only
- the reviewer can understand the scope in under five minutes
- tenant isolation is visible in the API structure and data model
- scoring rules are configurable and validated
- event-driven qualification can be demonstrated without external dependencies
- the implementation clearly distinguishes:
  - what is real in this slice
  - what is mocked
  - what is deferred from full V1
