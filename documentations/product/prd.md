# Product Requirements Document (PRD): Venture-Studio CRM

This PRD outlines the requirements, features, and phases for the Venture-Studio CRM (Multi-tenant Growth Engine).

---

## 1. Executive Summary
The Venture-Studio CRM is a multi-tenant platform designed to serve multiple startups under one studio. It allows portfolio startups to manage leads, track sales pipelines, automate outbound campaigns, and attribute revenue to marketing efforts, while maintaining absolute data isolation between tenants.

---

## 2. Scale Assumptions (V1 Design Envelope)

All architectural decisions and query strategies documented in this PRD are designed against the following scale envelope:

| Dimension | V1 Assumption | Notes |
|---|---|---|
| **Tenants (Startups)** | ~100 | Portfolio size of the Venture Studio |
| **Deals per Tenant** | ~100 | Average across active startups |
| **Total Deals (all tenants)** | ~10,000 | Primary driver for dashboard query load |
| **Leads per Tenant** | ~500 | Estimated active lead pipeline |
| **Total Leads (all tenants)** | ~50,000 | Secondary driver for outbound queue depth |
| **Active Outbound Enrollments** | ~5,000 | Upper bound on concurrent cron scheduler rows |

> **Note:** These are design-time assumptions. The system should be monitored against these bounds at production. See **Section 6 — Scale Revisit Thresholds** below for what needs re-evaluation if these limits are exceeded.

---

## 3. Target Audience
*   **Venture Studio Admins:** Need roll-up reporting and cross-tenant performance overview.
*   **Startup Admins/Growth Marketers:** Need to configure pipelines, scoring rules, and marketing attribution.
*   **Startup Sales Representatives (SDRs/AEs):** Need to manage leads, convert contacts, move deals, and review/send automated outbound sequences.

---

## 4. Release Phases & Scope

### Phase 1 (V1 Scope)
The initial release will focus on core B2B customer relationship operations, event-driven lead scoring, marketing attribution, and AI-powered sales outreach.

#### A. Tenant-Level Features (Startup Workspace)
These features are strictly isolated per startup tenant.

1.  **Lead Generation & Management:**
    *   Manual lead creation and management interface.
    *   API & Webhook connector layer for automated lead capture (e.g., from web forms, landing pages).
2.  **Deal Creation & Lifecycle Management:**
    *   Manual deal creation and stage progression.
    *   One-click Lead conversion (automatically creates Account, Contact, and Deal).
    *   Custom pipelines and stage configurations per tenant.
    *   Stage transition audit trails and simple forecasting engine.
3.  **Lead Scoring & Qualification:**
    *   Integration with **PostHog** for user event tracking (web visits, clicks).
    *   Tenant-specific scoring rules (Fit-based and Behavior-based).
    *   Automatic qualification transitions (Lead → MQL → SQL) based on scores and high-intent actions.
4.  **Performance Marketing Attribution:**
    *   Extraction of UTM parameters (`utm_source`, `utm_medium`, etc.) from PostHog events.
    *   Local database synchronization of UTM parameters for low-latency queries.
    *   Attribution dashboards tracking pipeline revenue and leads by campaign.
5.  **Outbound Automation:**
    *   **Pre-MQL (Rules & Static Templates):** Triggered multi-step email sequences based on static templates and delay day intervals, with stop criteria (replies, unsubscribes, stage change).
    *   **MQL (AI-Assisted Drafts):** LLM-generated drafts via a single base prompt utilizing tools (history, past emails) and a multi-step schedule (`delay_days`).
    *   **Human-in-the-Loop:** Drafts enter an approval queue. Reps can approve to send or reject. In V1, rejection simply skips the draft and the system schedules the next follow-up.
    *   **SQL (Manual Only):** Zero automated outbound; sales reps compose all communications manually to maintain high-touch relationships.

#### B. Studio-Level Features (Parent Workspace)
These features roll up data across all startups and allow parent-level defaults.

6.  **Venture Studio Parent Workspace (Super Admin Role):**
    *   Tenant switcher dropdown in the navigation header to toggle between startup instances.
    *   Rolled-up Sales Dashboard displaying aggregated pipeline metrics (Total Value, Total Won, Total Lost) for a date range across all startup tenants.
    *   Centralized default prompt and parameter templates for the AI Outbound Engine (which tenants can inherit or override).

---

### Phase 2 (V2 Scope - Deferred)
The following features are deliberately deferred to ensure a focused and robust V1 delivery.

#### A. Tenant-Level Features (Deferred)
1.  **Customer Success & Service (Support Ticketing):**
    *   Helpdesk ticketing system (ticket submission, assignments, status tracking, SLAs).
    *   Customer health scoring based on active product usage metrics.
    *   Automated CSAT / NPS (Net Promoter Score) surveys post-resolution or post-sale.
2.  **General Workflow Automation Engine:**
    *   Extensible webhook and action trigger builder (e.g., *"If Deal value > $10,000, trigger Slack alert to channel #sales"*).
    *   Integrations with third-party productivity apps (e.g., Slack, Notion, Jira).

#### B. Studio-Level Features (Deferred)
3.  **Advanced AI Reply Handling:**
    *   Fully automated categorization of inbound email replies (e.g., Interested, Not Interested, Out of Office).
    *   Auto-drafting of follow-up email replies for rep approval based on response sentiment.
4.  **Rolled-Up Marketing Attribution Dashboard:**
    *   Aggregated leads and pipeline revenue generated per UTM campaign/source across all startup tenants (parent workspace view).
    *   Powered by querying/aggregating PostHog event data from individual tenant projects.

---

## 5. General Tenant Security & Data Constraints

These constraints apply globally across all functionalities, tables, and services scoped under a startup workspace (Leads, Deals, Accounts, Contacts, etc.):

- **Strict Isolation:** Enforced via primary app-level scoping (`WHERE tenant_id = ?`) and PostgreSQL RLS as described in the [Multi-Tenancy Isolation Strategy](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/decisions/decisions.md#2-multi-tenancy-isolation-strategy).
- **Data Deletions:** All standard resource mutations use soft-deletes (setting a `deleted_at` timestamp) to prevent permanent accidental data loss.
- **Per-Tenant Uniqueness:** Unique indexes (such as email uniqueness) are enforced *per tenant* rather than globally. For example, `lead@example.com` can exist in Startup A and Startup B independently.

---

## 6. Scale Revisit Thresholds

This section documents explicit architectural components that require re-evaluation if the V1 scale assumptions (Section 2) are materially exceeded. All other components scale **operationally** (more queue workers, larger DB instance) without requiring design changes.

### 6.1 Super Admin Rolled-Up Sales Dashboard

- **Current V1 Design:** Queries are executed in real-time directly against the `Deal` and `DealPipelineStage` tables using a composite B-tree index on `(created_at, stage_id, amount) WHERE deleted_at IS NULL`. All queries are routed to a **read replica** via the `app_studio_user` role, ensuring zero impact on the primary transactional database. Expected end-to-end latency at 10K deals is **10–20ms** (steady-state) to **~50ms** (worst-case).
- **Revisit Trigger:** When total `Deal` rows across all tenants exceeds **~50,000** rows, or when dashboard P95 response latency exceeds **500ms** under concurrent Super Admin load.
- **Recommended Migration Path:**
  1. **50K–500K deals:** Retain direct SQL but ensure queries are exclusively routed to the read replica. Add a Redis TTL cache (10-minute TTL) keyed by `(start_date, end_date, tenant_filter_hash)` to absorb repeated identical requests.
  2. **500K+ deals:** Introduce a **two-tier aggregation strategy**:
     - A nightly scheduled job (via `pg_cron` or external cron) materializes daily pre-aggregated rollups into a `StudioSalesDailyRollup` table. Standard fixed date-range requests (last 7/30/90 days, last quarter) are served from this table at sub-millisecond latency.
     - Custom arbitrary date-range requests fall back to a bounded live SQL query on the read replica, with a rate limiter enforced per user session.
---

## 7. Functional Requirements & Scenarios

As we align on individual system scenarios, we will specify detailed functional requirements and reference their corresponding sequence diagrams here.

### A. Workspace & User Provisioning (Studio Bootstrap & Tenant Onboarding)

This scenario covers two sequential phases: studio-level setup (performed once by the Super Admin before any tenant is provisioned) and tenant provisioning (repeated for each new startup added to the portfolio).

> **RBAC Reference:** All access rules in this section derive from the combined identity role + active workspace context model. Refer to [Decision 6: RBAC Model](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/decisions/decisions.md#6-role-based-access-control-rbac-model) for the full permission matrix and DB role derivation.

---

#### Workflow 1: Studio Bootstrap (Super Admin First-Time Setup)

Performed **once** when the venture studio platform is first deployed. No tenant can be created or onboarded until this is complete.

- **System Bootstrapping:** The first Super Admin account is seeded directly into the database via a migration or CLI seed script. No public signup endpoint exists.
- **Forced Onboarding Checklist:** On first login, the Super Admin is presented with a mandatory setup checklist. They cannot navigate to any other part of the platform or create any tenant workspaces until all required items are complete:
  1. **Set AI Base Instruction (Required — Hard Gate):** The Super Admin must define the default `base_instruction` for AI-assisted outbound emails. This establishes the studio-wide default tone, brand voice, and compliance rules that all tenants inherit. Until this is saved, tenant creation is blocked.
- **Post-Bootstrap State:** Once the checklist is complete, the platform unlocks. The Super Admin lands on the Parent Workspace (studio context) and can begin provisioning tenant workspaces.

**Ongoing:** The Super Admin can update the `base_instruction` at any time from the studio settings. Refer to **Section 7.E.2 (AI Base Instruction Management)** for the update flow and its effect on tenant overrides.

---

#### Workflow 2: Tenant Provisioning & Member Onboarding

Performed for each new startup added to the portfolio.

- **Tenant Creation:** A logged-in Super Admin creates a new Tenant Workspace by providing metadata (e.g., Startup Name, Tenant ID, contact).
- **Tenant Admin Provisioning:** Along with tenant creation, the Super Admin inputs the email of the designated Tenant Admin (the startup's lead or administrator).
- **Activation Email Trigger:** The system generates a cryptographically secure, time-sensitive onboarding link (activation token with a configurable expiry, e.g., 48 hours) and sends an activation email to the Tenant Admin.
- **Password Setup:** The Tenant Admin clicks the activation link, submits a secure password, and activates their account.
- **Tenant Initial Setup (Onboarding Checklist):** After setting up credentials, the Tenant Admin must perform a one-time onboarding setup:
  1. *Website Tracking Setup:* The system programmatically provisions a separate organization and project in PostHog via the API, saving the resulting PostHog Project API Key and Project ID. The admin is presented with a pre-filled JavaScript snippet to embed on their website.
  2. *ICP Profile Setup:* The admin defines the startup's Ideal Customer Profile (ICP) including targeting rules (company size, industries, geographies, job titles).
  3. *Lead Generation Trigger Rules:* The admin configures event rules (e.g. which PostHog events trigger automated lead creation).
- **Delegated Team Provisioning (Self-Serve):** To eliminate operational bottlenecks at the Venture Studio level, the Tenant Admin can invite team members (e.g., Sales Reps, Growth Marketers) directly from their workspace settings by inputting their emails and selecting their roles.
- **Member Activation:** Invited members receive a secure activation email, set their passwords, and are granted access to that specific tenant workspace.

#### Key Rules & Constraints
- **Tenant Creation Gate:** A tenant workspace cannot be created if the Studio Bootstrap checklist (Workflow 1) is incomplete. Specifically, `base_instruction` must exist before any tenant can be provisioned.
- **Absolute Isolation:** Users provisioned under a specific tenant workspace are strictly restricted to that tenant's database partition/scope. They must not have access to metadata, leads, contacts, or deals belonging to other tenants.
- **Super Admin in Tenant Context:** When a Super Admin switches into a tenant workspace, they inherit full `tenant_admin` permissions for that workspace. Their identity role (`super_admin`) does not change — only the active workspace context in the JWT updates.
- **Token Validity:** Activation tokens must be single-use and expire after their configured duration. Clicking an expired or used token must display a clear validation error with an option to request a new link from the inviter.

#### Related Diagrams
- For the step-by-step sequence diagram of the initial workspace creation flow, refer to [1. Initial Tenant Registration & Delegation Flow](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/user-flows.md#1-initial-tenant-registration--delegation-flow).
- For the step-by-step sequence diagram of the onboarding and configuration flow, refer to [2. Tenant Initial Setup & Onboarding Flow](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/user-flows.md#2-tenant-initial-setup--onboarding-flow).


---

### B. Lead Management Service

This scenario covers two distinct workflows: tenant-driven CRUD operations and system-driven automated lead generation via async processing.

---

#### Workflow 1: CRUD Operations (Tenant-Driven)

All operations are scoped to the authenticated user's tenant. Standard CRUD is exposed via the API and enforced with RLS.

- **List / Read:** Startup members can view their tenant's lead records only. Supports filtering by status, source, owner, and date range.
- **Manual Create:** Permitted users create a lead by providing: Name, Email, Company, Source, Phone, Title, Notes. Email is mandatory and must be unique per tenant.
- **Update:** Permitted users can edit any lead field. All mutations are timestamped.
- **Delete:** Soft-delete only — sets `deleted_at`. Records are excluded from all views and API responses but retained for audit purposes.
- **Authorization:** Role-based. Sales Reps can create/update their own leads. Tenant Admins and Growth Marketers have broader access. Refer to [Multi-Tenancy Isolation Strategy](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/decisions/decisions.md#2-multi-tenancy-isolation-strategy) for role-level enforcement. (Can be taken in v2)

---

#### Workflow 2: Automated Lead Generation (System-Driven, Async)

Leads can be automatically created from user activity tracked via PostHog. This flow is processed entirely outside the request cycle by a dedicated **Lead Worker**.

##### Ingestion
- PostHog emits a webhook event for every tracked user action.
- The webhook destination in PostHog is configured with a filter: **only fire if the person's `email` or `phone` property is set** (i.e., identified users only). Anonymous events are dropped at source.
- A **Webhook Receiver** service accepts the inbound PostHog payload, validates the request signature, and publishes a typed job (e.g., `LEAD_GENERATION_JOB`) onto the message queue.

##### Processing (Lead Worker)
- The **Lead Worker** consumes jobs from the queue asynchronously.
- On receiving a `LEAD_GENERATION_JOB`, the worker:
  1. **Resolves the tenant** from the PostHog project/source identifier embedded in the payload.
  2. **Evaluates tenant rules:** Each tenant configures which event types (e.g., `pricing_page_viewed`, `demo_requested`) should trigger lead creation. The worker checks if the incoming event matches any active rule for that tenant.
  3. **Upserts the lead:** If the rule matches, the worker checks whether a lead with the given email already exists for that tenant.
     - If **new**: creates a lead record with identity fields populated from the PostHog person properties.
     - If **existing**: skips creation (no duplicate). Future enrichment updates are a V2 concern.
  4. **Logs the outcome** (created / skipped / rule-not-matched) for observability.
  5. **Notification Bypass (V1):** No notifications or alerts (such as email, push, or chat messages) are dispatched when a new lead is automatically ingested or assigned. These alerts are deferred to V2.
- If the worker fails mid-processing, the queue retries the job with backoff. Failed jobs beyond the retry limit are moved to a dead-letter queue for manual inspection.

##### Tenant Rule Configuration
- Tenant Admins can configure which PostHog event types act as lead generation triggers from within their workspace settings.
- A rule must specify at minimum: the **event name** to match. Additional property filters (e.g., `plan = enterprise`) can be layered on top.
- Only active rules are evaluated at processing time.

---

### C. Deal Creation & Lifecycle Management

This scenario covers pipeline stage customization, deal tracking, and basic sales forecasting.

#### 1. Custom Pipeline Stages
- **Default Stages:** Upon workspace registration, each tenant is provisioned with a default 6-stage pipeline:
  1. *Prospecting* (10% probability)
  2. *Qualification* (30% probability)
  3. *Proposal Sent* (60% probability)
  4. *Negotiation* (80% probability)
  5. *Closed Won* (100% probability)
  6. *Closed Lost* (0% probability)
- **Configuration:** Tenant Admins can customize their pipeline by adding, renaming, reordering, or deleting stages.
- **Conversion Probabilities:** Users can manually assign a conversion probability (0% to 100%) to each stage. Historical win-rate suggestions are deferred to V2.

#### 2. CRUD Operations on Deals
All deal operations are scoped to the authenticated user's tenant context.
- **Create:** Permitted users can create a deal record by specifying: Deal Name, Amount, Pipeline Stage, Expected Close Date, Associated Account/Contact, and Owner.
- **Read:** Users can view details and list all deals belonging to their tenant, with filters for owner, stage, close date range, and amount.
- **Update:** Users can move deals across stages or edit details. All updates are tracked with database-level timestamps.
- **Delete:** Soft-delete only (`deleted_at` timestamp).

#### 3. Weighted Sales Forecasting (Predicted Sales)
- **Calculation:** The system provides a simple weighted pipeline forecasting tool.
- **Formula:** For a user-selected Expected Close Date range, forecasted revenue is calculated on the fly as the sum of `Deal Amount * Current Stage Probability` for all active deals within that range.
- **Filtering:** Users can filter the forecast by date range, owner, or account.

---

### D. Outbound Automation Service

This scenario outlines the rules, templates, and AI orchestration parameters used to drive targeted email sequences across different prospect lifecycle stages.

#### 1. Pre-MQL Outbound (Rules & Static Templates)

*   **Tenant Configuration:**
    *   Startup admins can create, read, update, and delete outbound sequences using a standard CRUD interface.
    *   Each sequence requires: a name, a `trigger_type`, and an ordered list of steps (`StaticOutboundStep`).
    *   Each step links to a `StaticEmailTemplate` (supporting static HTML/text and basic merge tags like `{{first_name}}` and `{{company}}`) and specifies a `delay_days` value (where `0` denotes immediate delivery).
*   **Trigger Types:**
    *   `new_lead`: Evaluated immediately upon manual creation or automated PostHog ingestion of a new lead.
    *   `lead_event`: Evaluated when an existing Pre-MQL lead triggers a specific PostHog event matching the sequence's configured `trigger_event_name`.
*   **Enrollment Conflict & Lifecycle Rules:**
    *   **Single Active Enrollment:** A lead can only have one active sequence enrollment at any time. If a trigger occurs for a lead that already has an `active` enrollment in the database, the trigger is ignored and no new enrollment is created.
    *   **Stage Promotion Exit:** If a lead's stage is promoted beyond Pre-MQL (e.g., promoted to MQL or SQL), any active enrollment is immediately halted, and its status is updated to `cancelled_stage_promoted`.
*   **Scheduling & Execution Architecture:**
    *   **State-Driven Scheduling:** The `StaticOutboundEnrollment.next_step_due_at` timestamp serves as the scheduler state.
    *   **Cron Dispatcher:** A lightweight background cron job runs periodically (every 10 minutes) to query `StaticOutboundEnrollment` records where `status = 'active'` and `next_step_due_at <= NOW()`.
    *   **Queue-Based Worker:** For each due enrollment, the cron dispatcher publishes an immediate `OUTBOUND_EMAIL_JOB` to **BullMQ**. A dedicated **Outbound Worker** consumes the job, renders the template (resolving merge tags), and dispatches the email via the Email Service Provider (ESP) API.
    *   **Log & Next Step Calculation:** After dispatching the email, the worker logs the send event in the `StaticOutboundEmail` log (status = `sent`). It then calculates the next step:
        *   If additional steps remain in the sequence, the worker increments `current_step_position` and sets `next_step_due_at = NOW() + next_step.delay_days`.
        *   If no steps remain, the worker updates the enrollment status to `completed` and sets `next_step_due_at = NULL`.
*   **Stop Criteria:**
    *   **Hard Stop (Promotion):** Lead promotion to MQL/SQL updates status to `cancelled_stage_promoted` (halting future runs).
    *   **Soft Stop (Replies):** In V2, an ESP reply webhook will update the status to `paused_replied` for manual review by sales reps. In V1, reply handling is deferred.
    *   **Opt-Out (Unsubscribes):** In V1, the system relies entirely on the ESP's built-in suppression list to drop emails to unsubscribed addresses at the delivery layer; the CRM does not update enrollment state or record unsubscribe flags in V1 (deferred to V2).
*   **Workflow Reference:**
    *   For a complete visualization of this execution lifecycle, refer to [3. Pre-MQL Outbound Execution Flow](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/user-flows.md#3-pre-mql-outbound-execution-flow) in `user-flows.md`.

#### 2. MQL Outbound (AI-Assisted Drafts)
- **Triggers:** Transitions into the MQL status (`mql_promoted`).
- **Configuration & Prompting:**
  - **Single Base Prompt:** Tenants configure AI outreach via a single base instruction override (`AIPromptConfiguration`). This prompt dictates tone and product pitch. The AI dynamically decides the CTA based on past interactions. Missing configurations fallback to a studio-admin default.
  - **Step-based Scheduling:** Sequences use `AIOutboundStep` to define the number of follow-ups and the `delay_days` between them.
- **Orchestration:**
  - **Agentic Generation:** When a step is due, an AI Worker uses the `base_instructions` and explicitly defined function tools (e.g., `get_lead_details`, `get_past_emails`, `get_recent_website_events`) to dynamically decide the messaging context.
  - **Unified Approval Queue:** Generated emails land in `AIOutboundEmail` with a `pending_approval` status.
    - **Notification Bypass (V1):** No notifications or alerts (push notifications, email, Slack) are sent to reps when a draft is generated and queue-enrolled. Reps must check their approval queue view manually. Notifications are deferred to V2.
  - **Rejection Flow (V1):** If a Sales Rep rejects the draft, the email's status is set to `rejected` (no email is sent), and the system simply increments the step position to schedule the next follow-up. Full sequence discarding is deferred to V2.
- **Stop Criteria & Lifecycle Rules:**
  - **Hard Stop (Promotion to SQL):** If an MQL lead is promoted to SQL (or becomes a Deal), the active AI sequence enrollment is immediately halted, and its status is updated to `cancelled_stage_promoted`.
  - **Hard Stop (Demotion from MQL):** If an MQL lead is demoted back to Pre-MQL, the active AI sequence enrollment is immediately halted, and its status is updated to `cancelled_stage_demoted`.
  - **Soft Stop (Replies):** In V2, an ESP reply webhook will update the status to `paused_replied`. In V1, reply handling is deferred.

#### 3. SQL Outbound (Manual Only)
- **Rules:**
  - Automated or AI-assisted draft generation is disabled for leads that have reached the SQL / Deal stage.
  - All sales correspondence at this stage must be manually composed and sent by the assigned Sales Representative to preserve relationship integrity and alignment. (For v1)

---

### E. Parent Workspace (Super Admin View)

This section describes features available exclusively to Venture Studio Super Admins to monitor and analyze portfolio-wide performance.

#### 1. Rolled-Up Sales View (Dashboard)

*   **What it is:** A consolidated, read-only portfolio dashboard that aggregates sales pipeline metrics across all startup tenants (workspaces) under the Venture Studio. This dashboard is intended strictly for portfolio oversight, performance comparison, and aggregated forecasting.
*   **Access Control (Read-Only in V1):**
    *   This view is strictly read-only. Super Admins can view aggregated data across all tenants but cannot create, edit, or delete any records from the parent workspace.
    *   Access is governed by two things tracked independently: the user's **identity role** (fixed, stored in the user record) and their **active workspace context** (which workspace they are currently viewing, stored in the JWT). The role never changes; only the active workspace context changes when the tenant switcher is used.
    *   To take any action on a tenant's data, a Super Admin must switch to that tenant's workspace using the tenant switcher. This updates the active workspace context in the JWT — the Super Admin's identity role remains unchanged throughout.
*   **Data Covered:**
    *   **Underlying Entities:**
        *   `Tenant`: Used to group metrics by startup (e.g., startup name).
        *   `Deal`: Source of transactional amounts, creation timestamps, delete status (`deleted_at`), and pipeline stages.
        *   `DealPipelineStage`: Source of stage win probabilities, used for calculating active pipeline status and forecasting.
    *   **Dashboard Metrics:**
        *   **Total Deal Count:** Total number of non-deleted deals across all tenants (or filtered tenants) within the selected date range.
        *   **Active Pipeline Value:** Sum of `Deal.amount` for all active deals (where stage probability is between `1%` and `99%`).
        *   **Weighted Sales Forecast:** Sum of `Deal.amount * DealPipelineStage.probability` for all active deals.
        *   **Closed Won Value & Count:** Sum of `Deal.amount` and count of deals where stage probability is `100%` (`Closed Won`).
        *   **Closed Lost Value & Count:** Sum of `Deal.amount` and count of deals where stage probability is `0%` (`Closed Lost`).
    *   **Filtering:** Filterable globally and per-tenant by date range matching `Deal.created_at`.
*   **On-the-Fly Aggregation & SQL Index Optimization (V1 Strategy):**
    *   **Direct SQL Querying:** Rather than using complex synchronization pipelines, external key-value stores, or materialized views (which in PostgreSQL do not refresh automatically and would require intensive trigger/refresh logic), V1 performs aggregations **on-the-fly** directly against the transactional database tables.
    *   **Query Routing:** To prevent dashboard queries from impacting live transactional workloads, all parent workspace rollup queries are routed exclusively to a **read replica** database instance.
    *   **Composite Indexing:** The `Deal` table utilizes a B-tree composite index optimized for this query structure:
        *   Index definition: `CREATE INDEX idx_deals_rollup ON deals (created_at, stage_id, amount) WHERE deleted_at IS NULL;`
        *   This index allows the query planner to filter by date range, join with pipeline stages, and sum amounts directly from the index (Index-Only Scan), avoiding expensive heap scans.
    *   **Performance Expectation:** Based on the V1 design envelope of 100 tenants with ~100 deals each (10K total deals), on-the-fly SQL aggregation utilizing these indexes will execute in **10–20ms** (steady-state, warm buffer cache) to **~50ms** (worst-case: cold buffer cache, physical index page reads, WAL replay lag on the read replica) end-to-end. Both ranges are well within acceptable UI response budgets, making cached or pre-aggregated tables unnecessary for V1.
    *   **Scale Limits & Re-evaluation:** Refer to **Section 6.1 (Super Admin Rolled-Up Sales Dashboard)** for the migration path (Redis caching layer, then two-tier nightly aggregate table) if database deal volume exceeds the V1 design envelope.

---

#### 2. AI Base Instruction Management

*   **What it is:** The studio-wide default prompt instruction (`base_instructions`) that acts as the starting template for all AI-assisted outbound email generation across all tenant workspaces. Stored as a system-default record in `AIPromptConfiguration`. Tenants inherit this by default; they can optionally override it with a tenant-specific `AIPromptConfiguration` record.

*   **Super Admin: Set / Update Flow:**
    *   The Super Admin can view and edit the studio-wide `base_instructions` from the studio settings at any time (post-bootstrap).
    *   On save, the update takes effect for all tenants who have **not** overridden — their next AI draft generation will use the updated studio-wide instruction.
    *   Tenants who **have** overridden are completely unaffected. Their custom `base_instructions` remains the source of truth. Studio changes have zero effect on them.

*   **Data Model (AIPromptConfiguration):**
    *   **Studio Base Config:** A row in `AIPromptConfiguration` where `is_system_default = true` and `tenant_id = NULL`. The field `base_instructions` stores the studio default prompt.
    *   **Tenant Override Config:** A row in `AIPromptConfiguration` with the tenant's `tenant_id` and `is_system_default = false`. The field `base_instructions` stores the tenant's custom prompt override.
    *   **Resolution Logic:** At draft-generation time:
        ```sql
        -- Fetch active instruction: use tenant override if exists, fallback to studio default
        SELECT base_instructions 
        FROM ai_prompt_configurations 
        WHERE (tenant_id = :tenant_id AND is_system_default = false) 
           OR (is_system_default = true)
        ORDER BY is_system_default ASC 
        LIMIT 1;
        ```

*   **Tenant: Instruction Settings Page:**
    *   **If not overridden:** Tenant admin sees the studio-wide `base_instructions` as read-only, with a *"Customize for my workspace"* action to create an override (which creates a tenant-specific row in `AIPromptConfiguration`).
    *   **If overridden:** Tenant admin sees their own `base_instructions` override in edit mode. A collapsible *"View Studio Default"* panel shows the current studio-wide `base_instructions` for reference — so they can manually incorporate studio updates if they choose to.
    *   **Revert to Base:** Tenant admin can delete their override at any time (which deletes their tenant-specific row in `AIPromptConfiguration`), automatically reverting the workspace to the studio-wide default.

*   **Key Rules & Constraints:**
    *   Tenant overrides are fully isolated. Super Admin changes to the studio-wide `base_instructions` never propagate to tenants who have custom configurations.
    *   Tenant admins cannot see or edit another tenant's configuration.
    *   Super admins in tenant context (having switched workspaces) can view and edit the tenant's custom `base_instructions` with the same UX as a tenant admin.

---

## 8. To-Explore

Items listed here are **not decided** and have not been incorporated into the V1 design. They are flagged for future reading or evaluation before any implementation decision is made.

| Item | Context | Why Deferred |
|---|---|---|
| **BRIN Index on `Deal.created_at`** | Block Range Index — low-overhead range index suited for append-heavy, sequentially-inserted tables. Would complement the composite B-tree index on the `Deal` table for date-range scans. | Needs further reading on BRIN trade-offs (low cardinality selectivity, suitability vs B-tree for this access pattern) before deciding if it adds value at V1 scale. |



