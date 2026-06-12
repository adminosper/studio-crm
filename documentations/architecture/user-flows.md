# CRM System Sequence & Flow Diagrams

This document contains scenario-based sequence and flow diagrams illustrating various operational processes and interactions within the Venture-Studio CRM.

## User & Tenant Provisioning Flows

### 1A. Studio Bootstrap (Super Admin First-Time Setup)

This flow covers the **one-time** platform initialisation performed before any tenant can be provisioned. The Super Admin account is seeded via a DB migration/CLI script (no public signup). On first login, a mandatory checklist hard-gates all further access until the studio-wide AI Base Instruction is set.

```mermaid
sequenceDiagram
    autonumber

    participant DB as Database
    participant SA as Super Admin
    participant Sys as CRM System

    Note over DB,SA: Phase 1 — System Bootstrapping (one-time, pre-deploy)
    DB-->>SA: Seed Super Admin account via migration / CLI seed script
    Note right of DB: No public signup endpoint exists

    Note over SA,Sys: Phase 2 — First Login & Forced Onboarding Checklist
    SA->>Sys: Login with seeded credentials
    Sys-->>SA: Detect bootstrap_complete = false → Show Forced Onboarding Checklist
    Note right of Sys: All navigation & tenant creation blocked until checklist is complete

    Note over SA,DB: Checklist Step 1 (Required — Hard Gate)
    SA->>Sys: Set studio-wide AI Base Instruction (base_instructions)
    Sys->>DB: INSERT INTO ai_prompt_configurations (is_system_default=true, tenant_id=NULL, base_instructions=...)
    DB-->>Sys: Row created ✓
    Sys->>DB: SET bootstrap_complete = true on studio config
    DB-->>Sys: Updated ✓
    Sys-->>SA: Checklist complete — Platform unlocked

    Note over SA,Sys: Phase 3 — Post-Bootstrap State
    SA->>Sys: Navigate to Parent Workspace (studio context)
    Sys-->>SA: Parent Workspace dashboard loaded (read-only rollup view)
    Note right of Sys: SA can now create tenant workspaces
```

---

### 1B. Tenant Provisioning & Member Onboarding

This flow is **repeated for each new startup** added to the portfolio. It begins with the Super Admin creating a tenant workspace (only possible once Studio Bootstrap is complete) and ends with the startup's own team being fully onboarded in a self-serve manner.

```mermaid
sequenceDiagram
    autonumber

    participant DB as Database
    participant SA as Super Admin
    participant Sys as CRM System
    participant TA as Tenant Admin (Startup Head)
    participant Rep as Sales Rep

    Note over SA,Sys: Phase 1 — Tenant Workspace Creation
    SA->>Sys: Create new Tenant Workspace (e.g., "Startup A")
    Note right of Sys: Blocked if bootstrap_complete = false (base_instruction not set)
    SA->>Sys: Provide Tenant Admin email (startup's designated lead)
    Sys->>DB: INSERT Tenant record + User record (role = tenant_admin)
    DB-->>Sys: Tenant + User created ✓
    Sys->>Sys: Generate secure activation token (single-use, 48h expiry)
    Sys->>TA: Send Activation Email (with JWT token link)

    Note over TA,Sys: Phase 2 — Tenant Admin Account Activation
    TA->>Sys: Click activation link & submit password
    Sys->>DB: Validate token (single-use + not expired)
    alt Token valid
        Sys->>DB: Mark user as active, invalidate token
        Sys-->>TA: Account Activated ✓ — redirect to Onboarding Checklist
    else Token expired or already used
        Sys-->>TA: Error: token invalid — option to request new link from inviter
    end

    Note over TA,DB: Phase 3 — Tenant Onboarding Checklist (3 steps)
    Note right of TA: Refer to Flow 2 for full PostHog provisioning detail
    TA->>Sys: Step 1: Set up website tracking (PostHog org + project provisioned)
    TA->>Sys: Step 2: Define ICP profile (industries, geographies, company size, titles)
    TA->>Sys: Step 3: Configure lead generation trigger rules (e.g., pricing_page_viewed)
    Sys->>DB: Save ICP + trigger rules against tenant
    Sys-->>TA: Onboarding complete — Workspace ready

    Note over TA,Rep: Phase 4 — Delegated Team Provisioning (Self-Serve)
    TA->>Sys: Invite team member (email + role selection, e.g., Sales Rep)
    Sys->>DB: INSERT User record (role = sales_rep, tenant scoped)
    Sys->>Sys: Generate secure activation token (single-use, 48h expiry)
    Sys->>Rep: Send Activation Email (with JWT token link)
    Rep->>Sys: Click activation link & submit password
    Sys->>DB: Validate token → Mark user active, invalidate token
    Sys-->>Rep: Account Activated ✓ — Login to Startup A Workspace
```

---

## Lead Scoring & Lifecycle Flows

### 2. Lead Scoring & Qualification Pipeline

This flow covers the batch scoring process (triggered by cron or manual CTA), the HogQL aggregation of behavioral events, the evaluation of qualification thresholds, and the resulting stage transitions which emit events to halt or start outbound sequences.

```mermaid
sequenceDiagram
    autonumber

    participant CronScoring as Scoring Cron (Daily / 24h)
    participant TA as Tenant Admin (Manual CTA)
    participant Sys as CRM API (Scoring Engine)
    participant PH as PostHog API
    participant DB as Database
    participant MQ as Message Queue
    participant OW as Outbound Worker

    Note over CronScoring,Sys: Phase 1 — Triggering the Scoring Run
    alt Automated Daily Run
        CronScoring->>Sys: Execute Scoring Module (tenant_id=all, lead_id=null)
    else Manual Rescore (CTA)
        TA->>Sys: POST /scoring/recompute
        Sys->>Sys: Execute Scoring Module (tenant_id=current, lead_id=optional)
    end

    Note over Sys,DB: Phase 2 — Rule & Event Aggregation
    Sys->>DB: Load active LeadScoringRules for Tenant
    
    alt Behavior Rules Exist
        Sys->>PH: POST /api/projects/:id/query (HogQL)
        Note right of PH: SELECT person.properties.email, count() GROUP BY email
        PH-->>Sys: Aggregated event counts per email
    end

    Note over Sys,DB: Phase 3 — Score Computation & Stage Update
    Sys->>DB: SELECT * FROM leads WHERE status = 'active'
    loop For Each Active Lead
        Sys->>Sys: Calculate Fit Score (Lead firmographic fields vs. fit rules)
        Sys->>Sys: Calculate Behavior Score (PostHog aggregates vs. behavior rules, capped at 100)
        Sys->>Sys: new_score = sum(matched deltas), capped at 100

        alt is_stage_manually_overridden = false
            Sys->>Sys: Evaluate thresholds → new_stage (pre_mql / mql / sql)
        else
            Sys->>Sys: new_stage = old_stage (skip threshold evaluation)
        end

        Sys->>DB: UPDATE leads SET score=new_score, stage=new_stage, score_last_updated_at=NOW()

        alt Stage has changed
            Sys->>MQ: Publish LEAD_STAGE_CHANGED_JOB (lead_id, old_stage, new_stage)
        end
    end

    Note over MQ,OW: Phase 4 — Enrollment Lifecycle (Outbound Worker)
    MQ->>OW: Consume LEAD_STAGE_CHANGED_JOB

    alt Promoted: pre_mql → mql
        OW->>DB: UPDATE StaticOutboundEnrollment SET status='cancelled_stage_promoted'
        OW->>DB: INSERT AIOutboundEnrollment (step 1, next_step_due_at=NOW())
    else Promoted: mql → sql
        OW->>DB: UPDATE AIOutboundEnrollment SET status='cancelled_stage_promoted'
        Note right of OW: SQL stage — manual sales only, no auto enrollment
    else Demoted: mql → pre_mql
        OW->>DB: UPDATE AIOutboundEnrollment SET status='cancelled_stage_demoted'
        OW->>DB: INSERT StaticOutboundEnrollment (restart pre-mql sequence)
    end
```

---

### 3. Tenant Initial Setup & Onboarding Flow

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

### 4. Pre-MQL Outbound Execution Flow

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

### 5. MQL AI-Assisted Outbound Execution Flow

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

---

## Super Admin Parent Workspace Flows

### 6. Super Admin Parent Workspace Operations

This flow covers the three ongoing operational interactions available to Super Admins within the Parent Workspace (studio context): viewing the rolled-up portfolio dashboard, switching into a tenant workspace to take action, and managing the studio-wide AI Base Instruction (including its propagation and tenant override lifecycle).

#### 5A. Rolled-Up Sales Dashboard & Tenant Context Switching

```mermaid
sequenceDiagram
    autonumber

    participant SA as Super Admin
    participant Sys as CRM System
    participant RODB as Read Replica (PostgreSQL)
    participant DB as Primary DB (PostgreSQL)

    Note over SA,RODB: Phase 1 — Accessing the Portfolio Dashboard (Parent Workspace)
    SA->>Sys: Navigate to Parent Workspace dashboard
    Note right of Sys: JWT active_workspace_context = studio (no tenant_id)
    Sys->>RODB: On-the-fly aggregation query (via app_studio_user role)
    Note right of RODB: Uses idx_deals_rollup (created_at, stage_id, amount WHERE deleted_at IS NULL)
    RODB-->>Sys: Aggregated metrics per tenant (10–50ms at V1 scale)
    Sys-->>SA: Show read-only dashboard (Total Deals, Pipeline Value, Weighted Forecast, Won/Lost)
    Note right of SA: SA cannot create, edit, or delete records from Parent Workspace

    Note over SA,DB: Phase 2 — Switching into a Tenant Workspace to Take Action
    SA->>Sys: Select tenant from Tenant Switcher dropdown (e.g., "Startup A")
    Sys->>Sys: Issue new JWT: identity_role=super_admin, active_workspace_context=tenant_id_A
    Note right of Sys: Identity role (super_admin) never changes — only active workspace context updates
    Sys-->>SA: Tenant Workspace loaded — SA has full tenant_admin permissions within Startup A
    SA->>Sys: Perform action in tenant context (e.g., edit a lead, approve a draft)
    Sys->>DB: Tenant-scoped write (RLS enforced: tenant_id_A)
    DB-->>Sys: Write committed ✓
    Sys-->>SA: Action confirmed
```

---

#### 5B. AI Base Instruction Management (Super Admin Update Flow)

```mermaid
sequenceDiagram
    autonumber

    participant SA as Super Admin
    participant Sys as CRM System
    participant DB as Database
    participant AW as AI Worker (future draft generation)

    Note over SA,DB: Super Admin Updates Studio-Wide base_instructions (Post-Bootstrap, Ongoing)
    SA->>Sys: Navigate to Studio Settings → AI Base Instruction
    Sys->>DB: SELECT base_instructions FROM ai_prompt_configurations WHERE is_system_default = true
    DB-->>Sys: Current studio-wide base_instructions
    Sys-->>SA: Display current instruction in edit mode

    SA->>Sys: Submit updated base_instructions
    Sys->>DB: UPDATE ai_prompt_configurations SET base_instructions = :new WHERE is_system_default = true
    DB-->>Sys: Updated ✓
    Sys-->>SA: Save confirmed

    Note over DB,AW: Effect on Future Draft Generation
    Note right of DB: Tenants WITHOUT a custom override → next AI draft uses updated studio instruction
    Note right of DB: Tenants WITH a custom override (is_system_default=false) → completely unaffected

    Note over AW,DB: Resolution Query (per draft job)
    AW->>DB: SELECT base_instructions FROM ai_prompt_configurations\nWHERE (tenant_id = :tid AND is_system_default = false)\n   OR (is_system_default = true)\nORDER BY is_system_default ASC LIMIT 1
    alt Tenant has a custom override
        DB-->>AW: Returns tenant's custom base_instructions row
    else No tenant override exists
        DB-->>AW: Returns studio-wide base_instructions row (fallback)
    end
```

---

#### 5C. Tenant AI Base Instruction Override & Revert Lifecycle

```mermaid
sequenceDiagram
    autonumber

    participant TA as Tenant Admin
    participant Sys as CRM System
    participant DB as Database

    Note over TA,DB: Tenant Admin views AI Instruction Settings (no override exists)
    TA->>Sys: Navigate to Workspace Settings → AI Instruction
    Sys->>DB: CHECK ai_prompt_configurations WHERE tenant_id = :tid AND is_system_default = false
    DB-->>Sys: No row found
    Sys->>DB: Fetch studio default: WHERE is_system_default = true
    DB-->>Sys: Studio base_instructions (read-only for this tenant)
    Sys-->>TA: Display studio default as read-only + "Customize for my workspace" CTA

    Note over TA,DB: Tenant Creates a Custom Override
    TA->>Sys: Click "Customize for my workspace" → Edit & save custom base_instructions
    Sys->>DB: INSERT INTO ai_prompt_configurations (tenant_id=:tid, is_system_default=false, base_instructions=:custom)
    DB-->>Sys: Custom override created ✓
    Sys-->>TA: Custom instruction active — studio changes no longer affect this workspace

    Note over TA,DB: Tenant Admin Views Override (collapsible studio default reference)
    TA->>Sys: Navigate to Workspace Settings → AI Instruction
    Sys->>DB: SELECT base_instructions WHERE tenant_id=:tid AND is_system_default=false
    DB-->>Sys: Tenant's custom base_instructions
    Sys-->>TA: Display custom instruction in edit mode + collapsible "View Studio Default" panel

    Note over TA,DB: Tenant Reverts to Studio Default
    TA->>Sys: Click "Revert to Studio Default"
    Sys->>DB: DELETE FROM ai_prompt_configurations WHERE tenant_id=:tid AND is_system_default=false
    DB-->>Sys: Override deleted ✓
    Sys-->>TA: Reverted — workspace now inherits studio-wide base_instructions
    Note right of Sys: Next AI draft generation will use studio default (fallback resolution)
```
