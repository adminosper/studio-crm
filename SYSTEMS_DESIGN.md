# Systems Design Document: Venture-Studio CRM

This document serves as the primary systems design deliverable for the Venture-Studio CRM (Multi-tenant Growth Engine), summarizing the system architecture, database schema, isolation mechanics, design trade-offs, and scalability boundaries.

---

## 1. System Architecture

The CRM platform is structured to support real-time user interactions, asynchronous webhook integrations, and background scoring/marketing automation workloads.

*   **Architecture Blueprint:** The complete system architecture, container layers (Client Layer, External Layer, API Service, Ingestion Receiver, Workers, Schedulers), and service interactions are detailed in **[System Architecture (architecture.md)](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/architecture.md)**.
*   **Visual Diagrams:** Refer directly to:
    - **[Container Diagram (Clean View)](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/architecture.md#container-diagram-clean-view):** High-level view showing domain-grouped nodes and collapsed data paths.
    - **[Container Diagram (Detailed View)](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/architecture.md#container-diagram-detailed-view):** Detailed layout showing internal API submodules, queues, databases, and cron schedules.

---

## 2. Data Model & Schema

The platform maps B2B CRM structures (Leads, Accounts, Contacts, Deals) with Lead Scoring Rules, AI Prompt Configurations, and Outbound Email logs.

*   **ER Diagram & Specs:** The full database schema, indexes, field types, and notes are documented in **[Data Model (data-model.md)](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/data-model.md)**.
*   **Visual ER Diagram:** Refer to the **[Mermaid Entity-Relationship Diagram](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/data-model.md#entity-relationship-diagram)** showing all 21 entities and their explicit 26 relationships.

---

## 3. The Crux: Multi-Tenant Data Isolation

Under the Venture-Studio model, competitor startups share the same CRM database. Keeping their lead, contact, and deal records isolated is the most critical constraint.

*   **Database Level Isolation:** The CRM uses a shared-database, shared-schema design. Data is secured using PostgreSQL **Row-Level Security (RLS)**. Standard API sessions connect via the `app_tenant_user` database role, where access is strictly restricted by comparing the row `tenant_id` to the session context.
*   **Connection Pool Context Safety:** Because API and worker connections are pooled and multiplexed via PgBouncer, setting session-level configurations presents a security risk (context bleeding). We resolve this by enforcing:
    ```sql
    SET LOCAL app.current_tenant_id = 'uuid';
    ```
    The `SET LOCAL` command restricts the configuration value strictly to the active transaction block. Once the transaction commits or aborts, PostgreSQL automatically resets the setting, preventing context leakage to subsequent requests using the same connection.
*   **Tracking Isolation:** To prevent cross-startup data leaks in user tracking, the platform provisions a dedicated PostHog Organization and Project for each tenant startup. Webhook posts carry the unique PostHog project ID, which the CRM maps to the local tenant ID.
*   **Detailed RLS Policies:** For the full role definition matrix and database configuration code, refer to **[Design Decisions - Section 2 (decisions.md)](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/decisions/decisions.md#2-multi-tenancy-isolation-strategy)**.

---

## 4. Key Design Trade-offs

| Architectural Decision | Chosen Option | Rejected Alternative | Rationale |
|---|---|---|---|
| **Multi-Tenant Strategy** | Shared Database + PostgreSQL RLS | Database-per-Tenant or Schema-per-Tenant | Enforcing RLS on a shared database keeps migration management simple and connection overhead minimal, while allowing Super Admins to execute read-only cross-tenant sales aggregates easily without complex cross-DB joins. |
| **User Activity Ingestion** | PostHog JS SDK & Webhooks | Proprietary Custom Event Tracking Scripts | Offloads session management, browser fingerprinting, UTM campaign capture, and identity deduplication to an industry-standard SDK, avoiding massive custom telemetry development. |
| **Outbound Email Automation** | Segmented Outbound Channels (Static Pre-MQL, AI-Draft queue MQL, Manual SQL) | Full AI-driven reply and send automation | Protects unit economics (raw leads don't consume expensive LLM tokens) and protects brand voice (sales reps review and approve AI outbound drafts in a queue before they are sent). |
| **Sales Dashboard Rollups** | Direct SQL on Read Replica using index optimizations | Pre-aggregated caches or daily materialized tables | Eliminates cache invalidation lag, ensuring live forecast figures are 100% accurate. B-tree composite index `idx_deals_rollup` delivers sub-50ms performance at V1 scale (10K deals). |

---

## 5. What Scales and What Breaks (Scalability Limits)

### 5.1 Real-Time Super Admin Dashboard (Sales Rollup)
*   **What Breaks:** At scale (exceeding **50,000 deals** across all tenants), direct SQL aggregates over transactional tables on read replicas will suffer from page read latencies. P95 latency will exceed the 500ms UI budget.
*   **Scaling Path:**
    1. *Intermediate:* Wrap dashboard requests in a Redis TTL cache (10-minute expiry).
    2. *Scale:* Introduce a scheduled batch job to materialize daily aggregates into a `StudioSalesDailyRollup` table, serving standard date ranges instantly and falling back to bounded read-replica SQL for custom queries.

### 5.2 Outbound Sequence Scheduling
*   **What Breaks:** When active leads across portfolio startups exceed **50,000**, the dispatcher cron (polling database tables for due steps every 10 minutes) will execute queries that take longer than the cron interval, causing enqueuing race conditions and sending duplicates.
*   **Scaling Path:** Migrate the dispatcher from database polling to a **partitioned queue scheduler** (such as BullMQ or Celery). Partition the database queries by tenant ID ranges so workers execute queries concurrently in small, bounded chunks.

### 5.3 Behavior Aggregation & Scoring
*   **What Breaks:** Since HogQL queries are executed in bulk per rule per tenant (not per lead), rate limits are not a scaling bottleneck and scale horizontally using tenant-isolated API keys. However, executing live synchronous external API calls during the scoring run introduces **external network I/O latency** and a **hard dependency on PostHog's API availability**. If PostHog experiences downtime or network lag, the daily scoring execution fails or hangs.
*   **Scaling Path:** Replicate PostHog event streams directly to a local ClickHouse database replica (or a local PostgreSQL analytics table) in real time using PostHog webhooks or S3 export pipelines. The daily Scoring Engine queries this local replica, removing external network dependencies and latency entirely.
