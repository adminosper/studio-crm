# CRM System Sequence & Flow Diagrams

This document contains scenario-based sequence and flow diagrams illustrating various operational processes and interactions within the Venture-Studio CRM.

## User & Tenant Provisioning Flows

### 1. Initial Tenant Registration & Delegation Flow

This flow demonstrates how the system is bootstrapped, how the Super Admin creates a new startup tenant, and how user management is securely delegated to the startup's own admin.

```mermaid
sequenceDiagram
    autonumber
    
    participant DB as Database
    participant SA as Super Admin
    participant Sys as CRM System
    participant TA as Tenant Admin (Startup Head)
    participant Rep as Sales Rep

    Note over DB,SA: Phase 1: System Bootstrapping
    DB-->>SA: Seed initial Super Admin account (Direct DB Insertion)

    Note over SA,Sys: Phase 2: Tenant Creation
    SA->>Sys: Create new Tenant Workspace (e.g., "Startup A")
    SA->>Sys: Create first User for Tenant (Role: Tenant Admin)
    Sys->>TA: Send Activation Email (with secure JWT/token link)

    Note over TA,Sys: Phase 3: Tenant Admin Onboarding
    TA->>Sys: Click activation link & set password
    Sys-->>TA: Account Activated
    TA->>Sys: Login to Startup A Workspace

    Note over TA,Rep: Phase 4: Delegated Provisioning (Self-Serve)
    TA->>Sys: Invite new team member (Role: Sales Rep)
    Sys->>Rep: Send Activation Email (with secure JWT/token link)
    Rep->>Sys: Click activation link & set password
    Sys-->>Rep: Account Activated
    Rep->>Sys: Login to Startup A Workspace
```

---

### 2. Tenant Initial Setup & Onboarding Flow

This flow illustrates the post-login setup checklist completed by the Tenant Admin to establish tracking, configure the target client profile (ICP), and define the inbound triggers for automated lead generation.

```mermaid
sequenceDiagram
    autonumber

    participant TA as Tenant Admin
    participant CRM as CRM System
    participant PH as PostHog API
    participant DB as Database

    Note over TA,CRM: Tenant Admin has activated account & logged in

    CRM-->>TA: Show Onboarding Checklist (3 steps incomplete)

    Note over TA,PH: Step 1 — Website Tracking Setup

    TA->>CRM: Initiate "Set up website tracking"
    CRM->>PH: POST /api/organizations/ (create org for tenant)
    PH-->>CRM: organization_id
    CRM->>PH: POST /api/organizations/:org_id/projects/ (create project)
    PH-->>CRM: posthog_project_api_key, posthog_project_id
    CRM->>DB: Store posthog_project_api_key + posthog_project_id against tenant
    CRM-->>TA: Display JS tracking snippet (pre-filled with project api key)
    TA->>TA: Embed snippet on startup's website
    TA->>CRM: Mark tracking as configured

    Note over TA,DB: Step 2 — ICP Profile Setup (Firmographic Rules)

    TA->>CRM: Define ICP (industries, geographies, company size, titles)
    CRM->>DB: Save ICP profile configuration
    CRM-->>TA: ICP profile saved ✓

    Note over TA,DB: Step 3 — Lead Generation Trigger Rules

    TA->>CRM: Define event trigger rules (e.g., pricing_page_viewed)
    CRM->>DB: Save trigger rules to tenant settings
    CRM-->>TA: Rules saved ✓

    CRM-->>TA: Onboarding complete — workspace ready
```

---

## Outbound Automation Flows

### 3. Pre-MQL Outbound Execution Flow

This flow covers the runtime execution path for Pre-MQL outbound sequences: from a trigger event (new lead created or existing lead fires an event) through enrollment, scheduled execution via cron, and the stop conditions that cancel an active sequence.

> **Note:** Sequence and template *configuration* by the Tenant Admin is standard CRUD (not diagrammed here). This diagram focuses on the automated runtime path.

```mermaid
sequenceDiagram
    autonumber

    participant Trigger as Lead Worker / API
    participant DB as Database
    participant Cron as Cron Scheduler (every 10 min)
    participant MQ as Message Queue (BullMQ)
    participant OW as Outbound Worker
    participant ESP as Email Service Provider

    Note over Trigger,DB: Phase 1 — Enrollment Check & Creation

    Trigger->>DB: Lead created OR existing Pre-MQL lead fires event
    Trigger->>DB: Load active StaticOutboundSequence matching trigger_type
    DB-->>Trigger: Matching sequence(s) found

    Trigger->>DB: Check StaticOutboundEnrollment — is lead already active in a sequence?
    alt Lead already enrolled (status = active)
        DB-->>Trigger: Active enrollment found → IGNORE, do nothing
    else No active enrollment
        Trigger->>DB: Create StaticOutboundEnrollment (step 1, next_step_due_at = NOW(), status = active)
        DB-->>Trigger: Enrollment created ✓
    end

    Note over Cron,DB: Phase 2 — Scheduled Execution (runs every 10 min)

    Cron->>DB: SELECT enrollments WHERE next_step_due_at <= NOW() AND status = active
    DB-->>Cron: List of due enrollments

    loop For each due enrollment
        Cron->>MQ: Enqueue OUTBOUND_EMAIL_JOB (enrollment_id, step_position)
    end

    Note over MQ,ESP: Phase 3 — Outbound Worker Execution

    MQ->>OW: Consume OUTBOUND_EMAIL_JOB
    OW->>DB: Load enrollment, sequence, current StaticOutboundStep, StaticEmailTemplate
    OW->>OW: Render template (resolve merge tags: first_name, company, etc.)
    OW->>ESP: Send email via ESP API
    ESP-->>OW: Accepted (queued for delivery)
    OW->>DB: Insert StaticOutboundEmail log (status = sent)

    alt More steps remain in sequence
        OW->>DB: Update enrollment: current_step_position++, next_step_due_at = NOW() + next_step.delay_days
    else No more steps
        OW->>DB: Update enrollment: status = completed, next_step_due_at = NULL
    end

    Note over Trigger,DB: Phase 4 — Stop Conditions

    alt Lead is promoted to MQL (status change)
        Trigger->>DB: Find active StaticOutboundEnrollment for lead
        Trigger->>DB: Update enrollment: status = cancelled_stage_promoted, next_step_due_at = NULL
        Note right of DB: Hard Stop — MQL outbound flow takes over
    else Lead replies to email (V2 — ESP webhook)
        Trigger->>DB: Update enrollment: status = paused_replied, next_step_due_at = NULL
        Note right of DB: Soft Stop — Rep must manually resolve and restart outbound
    end
```

---

### 4. MQL AI-Assisted Outbound Execution Flow

This flow covers the generative loop and approval lifecycle for AI outbounds, operating off the array-based schedule.

```mermaid
sequenceDiagram
    autonumber

    participant Cron as Cron Scheduler
    participant MQ as Queue (BullMQ)
    participant AW as AI Worker
    participant LLM as LLM API
    participant DB as Database
    participant Rep as Sales Rep
    participant Trigger as Lead Worker / API

    Note over Cron,DB: Phase 1 — Draft Generation
    Cron->>DB: SELECT AIOutboundEnrollment WHERE next_step_due_at <= NOW()
    Cron->>MQ: Enqueue AI_DRAFT_JOB (enrollment_id, current_step_position)
    
    MQ->>AW: Consume Job
    AW->>DB: Fetch AIPromptConfiguration (Tenant or Fallback)
    
    loop Tool Calling Loop
        AW->>LLM: Generate draft (System Prompt + History)
        LLM-->>AW: Action: get_interaction_history()
        AW->>DB: Execute tool (RLS session bound to tenant)
        DB-->>AW: Tool Result
    end
    
    LLM-->>AW: Final Draft Subject & HTML
    AW->>DB: Insert AIOutboundEmail (status = pending_approval)

    Note over DB,Rep: Phase 2 — Human Approval & Execution
    Rep->>DB: Review pending AIOutboundEmail in Queue
    
    alt Rep Rejects Draft (V1 Flow)
        Rep->>DB: Mark email status = rejected
        Note right of DB: Draft skipped. No email sent.
        DB->>DB: Update Enrollment: current_step_position++, schedule next gap
    else Rep Approves Draft
        Rep->>DB: Mark email status = approved
        DB->>DB: Dispatch via ESP
        DB->>DB: Mark email status = sent
        DB->>DB: Update Enrollment: current_step_position++, schedule next gap
    end

    Note over Trigger,DB: Phase 3 — Stop Conditions

    alt Lead is promoted to SQL (status change)
        Trigger->>DB: Find active AIOutboundEnrollment for lead
        Trigger->>DB: Update enrollment: status = cancelled_stage_promoted, next_step_due_at = NULL
        Note right of DB: Hard Stop — AI sequence halted (moves to manual SQL)
    else Lead is demoted from MQL (status change)
        Trigger->>DB: Find active AIOutboundEnrollment for lead
        Trigger->>DB: Update enrollment: status = cancelled_stage_demoted, next_step_due_at = NULL
        Note right of DB: Hard Stop — AI sequence halted
    end
```
