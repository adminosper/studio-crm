# System Architecture

This document contains the high-level container architecture diagram for the Venture-Studio CRM platform. This is a first draft based on the workflows defined so far. It will be refined after the data modelling step and additional workflows.

---

## Container Diagram (V1 Draft)

```mermaid
flowchart TB
    subgraph Clients["Client Layer"]
        TUI["Tenant UI\n(Admin / Sales Rep / Marketer)"]
        SAU["Super Admin UI"]
    end

    subgraph External["External Services"]
        PH["PostHog\n(Per-Tenant Org & Project)"]
        SMTP["Email Service\n(SMTP / SendGrid)"]
        Web["Tenant Website\n(JS Snippet Embedded)"]
        LLM["LLM Service\n(Private Cloud / Enterprise API)"]
    end

    subgraph CRM["CRM Platform"]
        direction TB

        subgraph APIService["API Service"]
            direction LR
            MW["Auth & Tenant\nMiddleware\n(JWT + RLS context)"]
            CRUD["CRUD Handlers\n(Leads · Deals · Scoring Rules\nAccounts · Contacts · Pipeline\nICP · AI Draft Approvals)"]
            SCORE["Scoring Engine Module\n(Computes Fit + Behavior Score\n→ Updates Lead.score & Lead.stage)"]
            PROV["Provisioning Module\n(Tenant + PostHog Setup)"]
        end

        WR["Webhook Receiver Service\n(Thin HTTP Server)"]
        
        MQ[("Message Queue\n(Redis / BullMQ)")]
        
        LW["Lead Generation Worker Service\n(Job Consumer)"]
        
        CronScoring["Scoring Cron\n(Daily — Every 24h)"]

        CronOutbound["Outbound Dispatcher Cron\n(Every 10 min)"]
        
        OW["Outbound Worker Service\n(Job Consumer)"]

        AW["AI Worker Service\n(Job Consumer / LLM)"]

        DB[("PostgreSQL\nRLS Enabled\n+ PgBouncer")]
    end

    %% Client → API
    TUI -->|"REST API calls\n(CRUD & Manual CTA)"| MW
    SAU -->|"REST API calls"| MW
    MW --> CRUD
    MW --> PROV
    MW -->|"CTA Recompute\n(tenant_id=T, lead_id=optional)"| SCORE

    %% API → DB & SMTP
    CRUD -->|"Tenant-scoped\nqueries"| DB
    CRUD -->|"Send approved AI emails"| SMTP

    %% Provisioning
    PROV -->|"1. Create Org + Project\n2. Create Webhook Destination"| PH
    PROV -->|"Store PostHog keys\n+ Tenant record"| DB
    PROV -->|"Activation emails"| SMTP

    %% PostHog tracking
    Web -->|"JS Snippet\n(autocapture + identify)"| PH

    %% Webhook flow
    PH -->|"Webhook POST\n(identified users only)"| WR
    WR -->|"Validate signature\nEnqueue LEAD_GENERATION_JOB"| MQ
    MQ -->|"Consume job"| LW

    %% Lead Worker → DB (ingest + first enrollment)
    LW -->|"1. Resolve tenant\n2. Evaluate LeadTriggerRules\n3. Upsert Lead"| DB
    LW -->|"Check new_lead sequences\nCreate StaticOutboundEnrollment"| DB

    %% CRUD → first enrollment for manually created leads
    CRUD -->|"Check new_lead sequences\nCreate StaticOutboundEnrollment"| DB

    %% Daily Scoring Cron → Scoring Engine
    CronScoring -->|"Daily trigger\n(tenant_id=all, lead_id=null)"| SCORE
    SCORE -->|"Fetch behavioral aggregates via HogQL"| PH
    SCORE -->|"1. Read scoring rules & active leads\n2. Write scores & updated stages"| DB
    SCORE -->|"Publish LEAD_STAGE_CHANGED_JOB\n(if stage changed)"| MQ

    %% Stage transition → Outbound Worker handles enrollment lifecycle
    MQ -->|"Consume LEAD_STAGE_CHANGED_JOB"| OW
    OW -->|"Cancel old enrollment\nCreate new enrollment"| DB

    %% Outbound Dispatcher Cron (every 10 min)
    CronOutbound -->|"Query active static enrollments\nwhere next_step_due_at <= NOW()"| DB
    CronOutbound -->|"Enqueue OUTBOUND_EMAIL_JOB"| MQ
    MQ -->|"Consume OUTBOUND_EMAIL_JOB"| OW
    OW -->|"Render template, log send\nAdvance or complete enrollment"| DB
    OW -->|"Send Email"| SMTP

    %% Outbound Dispatcher Cron → AI draft flow
    CronOutbound -->|"Query active AI enrollments\nwhere next_step_due_at <= NOW()"| DB
    CronOutbound -->|"Enqueue AI_DRAFT_JOB"| MQ
    MQ -->|"Consume AI_DRAFT_JOB"| AW
    AW -->|"1. Fetch prompt config\n2. Execute RLS tools"| DB
    AW -->|"Generate draft"| LLM
    AW -->|"Insert AIOutboundEmail (pending_approval)"| DB

    %% Style definitions to override preview defaults (no yellow backgrounds)
    classDef neutral fill:#ffffff,stroke:#64748b,stroke-width:1px;
    classDef database fill:#f8fafc,stroke:#475569,stroke-width:2px;
    
    class TUI,SAU,PH,SMTP,Web,LLM,MW,CRUD,SCORE,PROV,WR,MQ,LW,CronScoring,CronOutbound,OW,AW neutral;
    class DB database;

    style Clients fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px
    style External fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px
    style CRM fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px
    style APIService fill:#ffffff,stroke:#cbd5e1,stroke-width:1px
```

---

## Container Diagram (V2 — Cleaner Layout)

> Same system, reorganised for readability. Nodes are grouped by domain. Arrows are collapsed (where multiple job types share the same path, they are listed on one edge label). Flow details live in the Workflow Coverage table and `user-flows.md` sequence diagrams.

```mermaid
flowchart LR
    subgraph Clients["Client Layer"]
        TUI["Tenant UI"]
        SAU["Super Admin UI"]
    end

    subgraph External["External Services"]
        PH["PostHog"]
        SMTP["Email Service\n(SendGrid)"]
        LLM["LLM Service"]
        Web["Tenant Website\n(JS Snippet)"]
    end

    subgraph CRM["CRM Platform"]

        subgraph API["API Service"]
            direction TB
            MW["Middleware\n(Auth · JWT · RLS)"]
            CRUD["CRUD Handlers\n(Leads · Deals · Scoring Rules\nAccounts · Contacts · ICP\nAI Draft Approvals)"]
            SCORE["Scoring Engine\n(Fit + Behavior → score & stage)"]
            PROV["Provisioning Module"]
            MW --> CRUD
            MW --> SCORE
            MW --> PROV
        end

        subgraph Ingestion["Async Ingestion"]
            direction TB
            WR["Webhook Receiver"]
            MQ[("Message Queue\n(Redis / BullMQ)")]
        end

        subgraph Schedulers["Scheduled Jobs"]
            direction TB
            CronScoring["Scoring Cron\n⏱ Every 24h"]
            CronOutbound["Outbound Dispatcher Cron\n⏱ Every 10 min"]
        end

        subgraph Workers["Worker Pool"]
            direction TB
            LW["Lead Generation Worker"]
            OW["Outbound Worker"]
            AW["AI Worker"]
        end

        DB[("PostgreSQL\n+ PgBouncer\n(RLS Enabled)")]
    end

    %% Client → API
    TUI & SAU -->|"REST"| MW

    %% Provisioning
    PROV -->|"Create Org/Project\n+ Webhook"| PH
    PROV --> DB & SMTP

    %% Web tracking
    Web -->|"JS Snippet"| PH

    %% Ingestion path
    PH -->|"Webhook POST"| WR
    WR -->|"LEAD_GENERATION_JOB"| MQ
    MQ -->|"LEAD_GENERATION_JOB"| LW
    LW -->|"Upsert Lead\n+ first enrollment"| DB

    %% CRUD → DB + first enrollment on manual lead create
    CRUD --> DB
    CRUD -->|"Send on AI draft approval"| SMTP

    %% Scoring engine
    CronScoring -->|"Daily trigger"| SCORE
    SCORE -->|"HogQL query"| PH
    SCORE --> DB
    SCORE -->|"LEAD_STAGE_CHANGED_JOB"| MQ

    %% Stage transition → Outbound Worker
    MQ -->|"LEAD_STAGE_CHANGED_JOB\nOUTBOUND_EMAIL_JOB"| OW
    OW --> DB & SMTP

    %% Outbound dispatcher
    CronOutbound -->|"OUTBOUND_EMAIL_JOB\nAI_DRAFT_JOB"| MQ
    MQ -->|"AI_DRAFT_JOB"| AW
    AW --> DB & LLM

    %% Styles
    classDef neutral fill:#ffffff,stroke:#64748b,stroke-width:1px;
    classDef database fill:#f8fafc,stroke:#475569,stroke-width:2px;
    classDef scheduler fill:#f0fdf4,stroke:#16a34a,stroke-width:1px;
    classDef worker fill:#f0f9ff,stroke:#0284c7,stroke-width:1px;

    class TUI,SAU,PH,SMTP,Web,LLM,MW,CRUD,SCORE,PROV,WR,MQ neutral;
    class LW,OW,AW worker;
    class CronScoring,CronOutbound scheduler;
    class DB database;

    style Clients fill:#f8fafc,stroke:#cbd5e1
    style External fill:#f8fafc,stroke:#cbd5e1
    style CRM fill:#f8fafc,stroke:#cbd5e1
    style API fill:#ffffff,stroke:#e2e8f0
    style Ingestion fill:#ffffff,stroke:#e2e8f0
    style Schedulers fill:#f0fdf4,stroke:#bbf7d0
    style Workers fill:#f0f9ff,stroke:#bae6fd
```

---

## Workflow Coverage

| Workflow | Services Involved |
|---|---|
| **1A. Studio Bootstrap** (Super Admin first-time setup, forced checklist, AI Base Instruction hard gate) | API Service (Provisioning Module) → DB |
| **1B. Tenant Provisioning & Member Onboarding** (SA creates workspace, TA activates & onboards, self-serve team invite) | API Service (Provisioning Module) → PostHog API + Email Service + DB |
| **2. Lead Management CRUD** (Tenant users manage leads) | API Service (CRUD Handlers) → DB |
| **3. Automated Lead Generation** (PostHog events → Lead records + first StaticOutboundEnrollment) | PostHog → Webhook Receiver → Queue → Lead Generation Worker → DB |
| **4. Manual Lead Creation** (Rep creates lead + first StaticOutboundEnrollment on new_lead trigger) | API Service (CRUD Handlers) → DB |
| **5. Daily Lead Scoring** (Batch scoring via HogQL, stage updates, stage-change event publication) | Scoring Cron (24h) / API Service (Manual CTA) → Scoring Engine → PostHog HogQL API & DB → Queue (LEAD_STAGE_CHANGED_JOB) |
| **6. Stage Transition Orchestration** (Cancel old enrollment, create new enrollment on stage change) | Queue → Outbound Worker Service → DB |
| **7. Deal Management** (Pipeline stages, deals, forecasting) | API Service (CRUD Handlers) → DB |
| **8. Pre-MQL Outbound Execution** (Dispatch due static emails every 10 min) | Outbound Dispatcher Cron (10 min) → DB → Queue (OUTBOUND_EMAIL_JOB) → Outbound Worker → DB & Email Service |
| **9. MQL AI-Assisted Draft Generation** (Generate & queue drafts for human approval every 10 min) | Outbound Dispatcher Cron (10 min) → DB → Queue (AI_DRAFT_JOB) → AI Worker → LLM → DB |
| **10. AI Draft Approval & Send** (Rep approves draft, email is dispatched) | API Service (CRUD Handlers) → DB & Email Service |
| **5A. Parent Workspace Dashboard & Tenant Switching** (SA views rolled-up metrics, switches tenant context via JWT) | API Service (CRUD Handlers) → Read Replica DB |
| **5B. AI Base Instruction Update** (SA updates studio-wide prompt, propagation to non-overriding tenants) | API Service (CRUD Handlers) → DB |
| **5C. Tenant AI Instruction Override & Revert** (Tenant Admin creates, edits, or deletes prompt override) | API Service (CRUD Handlers) → DB |

---

## Key Design Decisions Reflected

- **API Service and Async Layer are separate deployable units.** They share domain logic but scale independently — API scales with user request rate, Workers scale with queue depth.
- **One shared Webhook Receiver endpoint** handles events from all tenants. Tenant is resolved inside each job using the PostHog `project_id` → `tenant_id` DB lookup.
- **PostHog is configured per-tenant** (separate Org + Project + Webhook Destination), ensuring native event isolation without shared-schema filtering tricks.
- **PostgreSQL RLS** enforces data isolation at the DB level as a safety net. See [decisions.md](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/decisions/decisions.md).
- **PgBouncer** sits in front of PostgreSQL to multiplex connections from multiple API and Worker instances at scale.
- **Studio Bootstrap hard-gates tenant creation.** The `AIPromptConfiguration` system-default row (`is_system_default = true`) must exist before any tenant workspace can be provisioned. This is enforced at the API layer and guaranteed by the forced onboarding checklist on first Super Admin login.
- **Dual-context JWT model for Super Admins.** A Super Admin's `identity_role` is fixed in the user record. The `active_workspace_context` (studio or a specific `tenant_id`) is updated in the JWT when the tenant switcher is used. This allows the API to enforce the correct permission set (read-only rollup vs. full tenant-admin CRUD) without altering the user's identity.
- **Parent Workspace dashboard queries are routed exclusively to the Read Replica** via the `app_studio_user` DB role, isolating portfolio-wide aggregation from the primary transactional workload. At V1 scale (~10K deals), on-the-fly SQL with the `idx_deals_rollup` composite index delivers results in 10–50ms with no caching layer needed.
- **AI Base Instruction uses a single-table fallback pattern.** One `AIPromptConfiguration` row with `is_system_default = true` holds the studio default. Tenant overrides are opt-in rows with `is_system_default = false`. The AI Worker resolves the active instruction at draft-generation time via an `ORDER BY is_system_default ASC LIMIT 1` query — tenant override wins if present, studio default is the fallback.
- **AI Tool Data Isolation & Security:** All LLM tools (function calls) executed by the AI Worker are constrained by PostgreSQL Row-Level Security (RLS) bound to the active tenant's context, preventing prompt hallucinations from cross-contaminating tenant boundaries.
- **LLM Data Privacy:** Decoupled architecture interfaces with a private cloud LLM or Enterprise API endpoint to guarantee zero utilization of tenant data for model training.
