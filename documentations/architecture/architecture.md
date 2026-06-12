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
            CRUD["CRUD Handlers\n(Leads · Deals · Accounts\nContacts · Pipeline · ICP\nAI Draft Approvals)"]
            PROV["Provisioning Module\n(Tenant + PostHog Setup)"]
        end

        WR["Webhook Receiver Service\n(Thin HTTP Server)"]
        
        MQ[("Message Queue\n(Redis / BullMQ)")]
        
        LW["Lead Generation Worker Service\n(Job Consumer)"]
        
        Cron["Cron Scheduler Service\n(Timer / Dispatcher)"]
        
        OW["Outbound Worker Service\n(Job Consumer)"]

        AW["AI Worker Service\n(Job Consumer / LLM)"]

        DB[("PostgreSQL\nRLS Enabled\n+ PgBouncer")]
    end

    %% Client → API
    TUI -->|"REST API calls"| MW
    SAU -->|"REST API calls"| MW
    MW --> CRUD
    MW --> PROV

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

    %% Lead Worker → DB
    LW -->|"1. Resolve tenant\n2. Evaluate rules\n3. Upsert Lead"| DB
    
    %% Pre-MQL Outbound Flow
    Cron -->|"Query due enrollments"| DB
    Cron -->|"Enqueue OUTBOUND_EMAIL_JOB"| MQ
    MQ -->|"Consume job"| OW
    OW -->|"Render templates\nUpdate state"| DB
    OW -->|"Send Email"| SMTP

    %% MQL AI-Assisted Outbound Flow
    Cron -->|"Query due AI enrollments"| DB
    Cron -->|"Enqueue AI_DRAFT_JOB"| MQ
    MQ -->|"Consume job"| AW
    AW -->|"1. Fetch prompt config\n2. Execute RLS tools"| DB
    AW -->|"Generate drafts"| LLM
    AW -->|"Insert pending AI drafts"| DB

    %% Style definitions to override preview defaults (no yellow backgrounds)
    classDef neutral fill:#ffffff,stroke:#64748b,stroke-width:1px;
    classDef database fill:#f8fafc,stroke:#475569,stroke-width:2px;
    
    class TUI,SAU,PH,SMTP,Web,LLM,MW,CRUD,PROV,WR,MQ,LW,Cron,OW,AW neutral;
    class DB database;

    style Clients fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px
    style External fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px
    style CRM fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px
    style APIService fill:#ffffff,stroke:#cbd5e1,stroke-width:1px
```

---

## Workflow Coverage

| Workflow | Services Involved |
|---|---|
| **1. Provisioning** (Super Admin creates tenant, Tenant Admin onboards) | API Service (Provisioning Module) → PostHog API + Email Service + DB |
| **2. Lead Management CRUD** (Tenant users manage leads) | API Service (CRUD Handlers) → DB |
| **3. Automated Lead Generation** (PostHog events → Lead records) | PostHog → Webhook Receiver Service → Queue → Lead Generation Worker Service → DB |
| **4. Deal Management** (Pipeline stages, deals, forecasting) | API Service (CRUD Handlers) → DB |
| **5. Pre-MQL Outbound Automation** (Scheduled email dispatch) | Cron Scheduler Service → DB → Queue → Outbound Worker Service → DB & Email Service |
| **6. MQL AI-Assisted Outbound Automation** (Scheduled draft generation & approval) | Cron Scheduler Service → DB → Queue → AI Worker Service (calling LLM) → DB; API Service (CRUD Handlers) → DB & Email Service |

---

## Key Design Decisions Reflected

- **API Service and Async Layer are separate deployable units.** They share domain logic but scale independently — API scales with user request rate, Workers scale with queue depth.
- **One shared Webhook Receiver endpoint** handles events from all tenants. Tenant is resolved inside each job using the PostHog `project_id` → `tenant_id` DB lookup.
- **PostHog is configured per-tenant** (separate Org + Project + Webhook Destination), ensuring native event isolation without shared-schema filtering tricks.
- **PostgreSQL RLS** enforces data isolation at the DB level as a safety net. See [decisions.md](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/decisions/decisions.md).
- **PgBouncer** sits in front of PostgreSQL to multiplex connections from multiple API and Worker instances at scale.
- **AI Tool Data Isolation & Security:** All LLM tools (function calls) executed by the AI Worker are constrained by PostgreSQL Row-Level Security (RLS) bound to the active tenant's context, preventing prompt hallucinations from cross-contaminating tenant boundaries.
- **LLM Data Privacy:** Decoupled architecture interfaces with a private cloud LLM or Enterprise API endpoint to guarantee zero utilization of tenant data for model training.
