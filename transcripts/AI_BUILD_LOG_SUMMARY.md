# AI Build Log Summary: Venture-Studio CRM

This document summarizes the collaborative human-AI development process for the **Venture-Studio CRM** project, illustrating how the AI IDEs were steered, how project constraints and guidelines were enforced via `AGENTS.md`, and detailing critical instances of course correction.

It was prepared against the submission requirements in `problem-statement/problem-statement-doc-format copy.docx` and uses both the planning/documentation transcripts and the working Codex implementation transcript.

---

## 1. IDE & Model Environment

Two AI IDEs were used with clearly separated responsibilities:

*   **Codex**:
    *   Used for implementing the working backend feature slice.
    *   Responsible for the actual FastAPI/PostgreSQL coding work, repository refactors, scoring engine implementation, route wiring, and automated tests.
    *   Operated through command execution, file inspection, and patch-based code edits inside the repo workspace.

*   **Antigravity Code IDE**:
    *   Used primarily for planning, documentation, system-design iteration, and brainstorming.
    *   **Claude Sonnet** was used for the more critical technical brainstorming, tradeoff analysis, and design exploration.
    *   **Gemini Flash** was used for more straightforward documentation updates, formatting work, and instruction-following tasks.
    *   This track also handled document extraction/inspection flows and transcript organization for the broader design exercise.

At a practical level, the split was:

*   **Codex** -> working implementation
*   **Antigravity** -> planning, domain-knowledge discovery, and documentation

> **Note on Platform Roles**: All domain understanding, glossary discovery, and business rule mapping were conducted exclusively on the **Antigravity** platform to keep the entire planning-related transcript history in one central place (to capture all discussions in JSONL transcripts). While in other scenarios, high-level brainstorming and domain discovery could be handled using general-purpose LLMs (rather than coding agents), using the Antigravity agent ensured that design context, requirements details, and files were co-located in the same workspace thread.

### Transcript Sources Used For This Summary

The summary below was compiled from the following sources:

*   Submission requirements from `problem-statement/problem-statement-doc-format copy.docx`
*   Antigravity planning/documentation transcripts:
    *   `transcripts/antigravity/transcript_012fc624-9d9f-4c19-8944-30f01d90a57c.jsonl`
    *   `transcripts/antigravity/transcript_bff86c24-236e-4b32-a3aa-0ce4ba27ae7d.jsonl`
*   Codex implementation/debugging transcript:
    *   `transcripts/codex/rollout-2026-06-12T19-19-25-019ebc18-3ae4-74e1-88ec-81ca19ba7c84.jsonl`

This matters because the Antigravity transcripts capture the planning and design iterations, while the Codex transcript captures the implementation-side review feedback, debugging, schema corrections, and API contract refinements that were part of the actual build.

---

## 2. Steering & Collaborative Methodology

Rather than letting the AI agent write code unprompted, the development process was driven through a **planning-first, collaborative feedback loop**:
1.  **Brainstorming & Scoping**: Aligning on feature definitions (MQL/SQL thresholds, Lead statuses, outbound sequence timing) before committing to PRD changes.
2.  **Strict Layering & Design Verification**: Mapping databases, entities, and flow transitions step-by-step prior to writing any API route or scoring engine logic.
3.  **Active Verification**: Running test suites immediately after code edits to isolate bugs and ensure structural integrity.

---

## 3. Enforcement of Development Rules (`AGENTS.md`)

The file [AGENTS.md](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/AGENTS.md) was provided as a strict context boundary. The agent adhered to these constraints throughout the coding phase:

*   **One Responsibility per File (Layering)**: 
    *   Scoring algorithms were separated into `fit_scorer.py` and `behavior_scorer.py` under `src/services/lead_scoring_engine/`.
    *   API endpoints were kept clean in `src/routes/scoring_compute.py`, with query and update behaviors delegated to services and repositories.
*   **Centralized Configuration**: All variables (PostHog connection details, DB parameters) were loaded from centralized configuration helpers rather than inline hardcoding.
*   **Explicit Error Handling**: Exceptions were caught at the integration borders (such as mock PostHog response failures) and logged, returning safe, decoupled schemas to the client.
*   **Testing Expectations**: Every new component was shipped with comprehensive unit tests co-located in `tests/services/lead_scoring_engine/` and `tests/integrations/posthog/`, achieving test coverage for both happy paths and failure bounds.

---

## 4. Planning-Time Pushbacks (Antigravity)

These examples are from the planning/documentation track, where the user used Antigravity primarily for architecture, scoping, and design clarification rather than code generation.

### Example 1: The "Defer The Opt-Out Toggle To Keep V1 Sharp" Pushback
*   **Context**: *Antigravity session `bff86c24`, AI outbound configuration and data-model review*
*   **The AI Failure**: The planning artifacts still carried a per-tenant `ai_outbound_enabled` toggle and its related lifecycle behavior, which was starting to add more entity and workflow complexity than the user wanted for the constrained V1 scope.
*   **The User's Feedback**:
    > "cool. Lets defer opt out option to v2. Add in decisions. This way we don't have to make any changes in entity structure. Because of time constraints we can prioritise this feature later."
*   **How We Course-Corrected**: The planning track explicitly pushed the opt-out toggle to V2, removed the need for an extra boolean on the tenant model for V1, and documented the product decision in `decisions.md`. That kept the admin/user-flow design cleaner and prevented the PRD and data model from carrying a half-scoped control surface that the implementation was not going to support.

### Example 2: The "Fix The Real V1 Scope, Not The Assumed Scope" Pushback
*   **Context**: *Antigravity session `012fc624`, PRD/system-design alignment*
*   **The AI Failure**: The PRD draft still treated one-click lead conversion as active V1 scope, even though the broader functional design had already evolved and no such concrete implementation path had been agreed.
*   **The User's Feedback**:
    > "One-click Lead conversion (automatically creates Account, Contact, and Deal). (This is wrong we have not designed system with this requirement.) Review all the system design (assignment blueprint) with the ones written in functional requirements section because it contains actual v1 and deferred (v2) related entries. Update this system design scope with right scope."
*   **How We Course-Corrected**: The planning artifacts were re-baselined around the actually agreed slice. Automatic conversion language was removed from active scope, deferred items were clearly split into V2, and the PRD/system-design documents were made consistent with the functional-requirement decisions rather than with earlier assumptions.

### Example 3: The "RBAC And Admin Flows Need A Real Model" Pushback
*   **Context**: *Antigravity session `bff86c24`, studio bootstrap / admin provisioning / AI base-instruction design*
*   **The AI Failure**: The initial planning state around Super Admin behavior, tenant context, and AI prompt configuration was too loose. It risked leaving the PRD with generic admin wording and an under-modeled prompt configuration story.
*   **The User's Feedback**:
    > "Think of all the RBAC - think what is the right way to define it and where to define it."
    > "Admin role will have update option of base instruction."
    > "Once admin gets into tenant view then anyway it will have access like a tenant role so we don't need to worry about it."
*   **How We Course-Corrected**: The planning track converged on a context-based RBAC model: `super_admin` in `studio` context remains read-only at the roll-up layer, but inherits tenant-admin capabilities when switched into `tenant:<id>` context. This also forced a cleaner studio-bootstrap design where base instruction setup becomes a hard gate before tenant provisioning. The AI instruction model was then realigned to a proper `AIPromptConfiguration` entity instead of vague per-tenant text fields.

### Example 4: The "PostHog Scaling Assumption Was Wrong" Pushback
*   **Context**: *Antigravity session `012fc624`, scalability review for lead-scoring and attribution*
*   **The AI Failure**: The AI claimed that tenant-scoped aggregation through PostHog would primarily break due to shared API rate limits, and started steering the architecture toward a more dramatic replication story.
*   **The User's Feedback**:
    > "Behavir aggregation is incorrect, we can call posthog aggreagtion apis per tenant level. So what breaks is incorrect - don't you think ?"
*   **How We Course-Corrected**: The design analysis was corrected to reflect the actual tenancy model. Since each tenant owns isolated PostHog project credentials, the architectural problem is not a single shared global rate-limit bottleneck; it is dependency on external analytics latency and availability. That changed the planning narrative from “global API limits break first” to “network I/O and external-service dependency are the real scaling risks.”

## 5. Coding-Time Pushbacks (Codex)

These examples are from the implementation track, where the user pushed back directly on schema design, module structure, API semantics, and scoring-engine behavior while the working FastAPI slice was being built.

### Example 1: The "Schema Must Match The Agreed Slice" Pushback
*   **Context**: *Codex transcript `rollout-2026-06-12T19-19-25-019ebc18-3ae4-74e1-88ec-81ca19ba7c84`, Milestone 1 schema review*
*   **The AI Failure**: The first implementation pass drifted from the exact scoped prototype. It introduced config that was not needed and missed fields that were already agreed in the data model.
*   **The User's Feedback**:
    > "App_name in env not required."
    > "You have not added deleted_at in tenant table..."
    > "You jmissed phone as well from leads table."
    > "No need to maintain lead_score_runs for now..."
*   **How We Course-Corrected**: The implementation was pulled back to the precise prototype boundary. `deleted_at` was restored to `tenants`, `phone` was restored to `leads`, non-essential config was removed, and premature run-tracking persistence was dropped because observability was explicitly out of scope for this assignment slice.

### Example 2: The "Scoring API Must Reflect Real Stored Semantics" Pushback
*   **Context**: *Codex transcript `rollout-2026-06-12T19-19-25-019ebc18-3ae4-74e1-88ec-81ca19ba7c84`, scoring-engine contract review*
*   **The AI Failure**: The scoring engine exposed transient compute fields and inconsistent naming. The service also drifted from the actual persisted semantics by leaking internal concepts like `skip_reason`, `fit_score_delta`, and `behavior_score_delta`.
*   **The User's Feedback**:
    > "Instead of naming it recompute lets name it compute/generate something."
    > "What is skip_reason ??"
    > "You have defined contract of compute_tenant_scores ... but you are not using it..."
    > "In the db field name is just score, where are you checking ??"
*   **How We Course-Corrected**: The external contract was tightened around what the system truly stores and guarantees. Internal skip bookkeeping remained internal, the typed response model was wired into the service properly, and the naming was moved toward clearer compute semantics instead of leaking implementation noise to the API layer.

### Example 3: The "Technical Decisions Continue During Coding, Not Just In Planning" Pushback
*   **Context**: *Codex transcript `rollout-2026-06-12T19-19-25-019ebc18-3ae4-74e1-88ec-81ca19ba7c84`, scoring-engine behavior and normalization review*
*   **The AI Failure**: Several behavior decisions in the scoring engine were still underspecified during implementation: naming, score capping, normalization semantics, and transaction behavior could easily have been left implicit or inconsistent.
*   **The User's Feedback**:
    > "Lets keep score cap to <= 100..."
    > "if score is more than 100, then lets normalise based on proportion..."
    > "compute should be in a transaction."
    > "behavior_aggregator is just posthog aggregation mock right ??"
*   **How We Course-Corrected**: The coding track did not treat these as minor implementation details. Score normalization became a documented contract, compute stayed transactional, and the PostHog aggregation layer was explicitly framed as a mock integration boundary rather than as a hidden internal shortcut. This is important because those decisions now live both in code and in the accompanying rule-contract/decision documentation.

---

## 6. Key Takeaways

1.  **AI is prone to premature optimization and updates**: The agent often tries to jump directly to modifying files or writing code. Direct instructions to pause, opine, and brainstorm are required to control scoping.
2.  **Context and boundaries prevent drift**: Constraining the agent with files like `AGENTS.md` keeps code clean and modular, saving hours of refactoring.
3.  **Active checking (running scripts/tests) is crucial**: When the agent encountered non-standard file formats (like `.docx`), standard scripting tools helped bypass library limitations to get the source truth.
