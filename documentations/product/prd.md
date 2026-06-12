# Product Requirements Document (PRD): Venture-Studio CRM

This PRD outlines the requirements, features, and phases for the Venture-Studio CRM (Multi-tenant Growth Engine).

---

## 1. Executive Summary
The Venture-Studio CRM is a multi-tenant platform designed to serve multiple startups under one studio. It allows portfolio startups to manage leads, track sales pipelines, automate outbound campaigns, and attribute revenue to marketing efforts, while maintaining absolute data isolation between tenants.

---

## 2. Target Audience
*   **Venture Studio Admins:** Need roll-up reporting and cross-tenant performance overview.
*   **Startup Admins/Growth Marketers:** Need to configure pipelines, scoring rules, and marketing attribution.
*   **Startup Sales Representatives (SDRs/AEs):** Need to manage leads, convert contacts, move deals, and review/send automated outbound sequences.

---

## 3. Release Phases & Scope

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
    *   Rolled-up Marketing Dashboard displaying aggregated leads and pipeline revenue generated per UTM campaign/source across all startup tenants.
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

---

## 4. General Tenant Security & Data Constraints

These constraints apply globally across all functionalities, tables, and services scoped under a startup workspace (Leads, Deals, Accounts, Contacts, etc.):

- **Strict Isolation:** Enforced via primary app-level scoping (`WHERE tenant_id = ?`) and PostgreSQL RLS as described in the [Multi-Tenancy Isolation Strategy](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/decisions/decisions.md#2-multi-tenancy-isolation-strategy).
- **Data Deletions:** All standard resource mutations use soft-deletes (setting a `deleted_at` timestamp) to prevent permanent accidental data loss.
- **Per-Tenant Uniqueness:** Unique indexes (such as email uniqueness) are enforced *per tenant* rather than globally. For example, `lead@example.com` can exist in Startup A and Startup B independently.

---

## 5. Functional Requirements & Scenarios

As we align on individual system scenarios, we will specify detailed functional requirements and reference their corresponding sequence diagrams here.

### A. Workspace & User Provisioning (Tenant & Member Onboarding)
This scenario outlines how workspace instances are initialized, how startups are added, and how users are securely provisioned through a delegated model.

#### 1. Core Workflow
- **System Bootstrapping:** Initial Super Admin credentials and roles are seeded directly in the database (via migrations or CLI seed scripts) rather than exposing a public signup endpoint.
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

#### 2. Key Rules & Constraints
- **Absolute Isolation:** Users provisioned under a specific tenant workspace are strictly restricted to that tenant's database partition/scope. They must not have access to metadata, leads, contacts, or deals belonging to other tenants.
- **Super Admin Scope:** Super Admins have a global context, enabling them to switch workspaces dynamically via a tenant-selector interface.
- **Token Validity:** Activation tokens must be single-use and expire after their configured duration. Clicking an expired or used token must display a clear validation error with an option to request a new link from the inviter.

#### 3. Related Diagrams
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


