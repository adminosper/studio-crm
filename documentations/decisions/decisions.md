# Design Decisions

## 1. CRM Scope: B2B Focus
* **Decision:** We will restrict the initial scope of the Venture-Studio CRM to B2B (Business-to-Business) scenarios.
* **Details:**
  * The system will center around the standard B2B entities: **Leads**, **Accounts** (companies), **Contacts** (individuals within those companies), and **Deals** (sales pipelines).
  * While the architecture can be extended or repurposed for D2C/B2C transactional models in the future, focusing on B2B aligns with the typical venture-studio startup tracking needs and ensures a clear data model definition for the MVP.

---

## 2. Multi-Tenancy Isolation Strategy

* **Decision:** Startups (tenants) share the same database tables. Data is isolated using a double-layer strategy:
  1. **Application-Level Scoping (Primary):** The application code always filters queries using `tenant_id`.
  2. **Database-Level Row-Level Security (RLS) (Safety Net):** PostgreSQL enforces that queries can only see or modify rows matching the session's active tenant.
* **Why this approach:** It allows the Super Admin to run cross-tenant rollup metrics easily (which separate databases/schemas would make highly complex), while providing a hard database-level safeguard against accidental cross-tenant data leaks.

---

### Database Roles & Policies

We define two database roles to enforce isolation:
* **`app_tenant_user` (Tenant Admins & Sales Reps):** PostgreSQL Row-Level Security (RLS) is enabled on all tenant-scoped tables. Data is isolated by comparing the `tenant_id` of each row against the session's active tenant ID. If they do not match, access/modification is blocked (fails closed if session context is unset).
* **`app_studio_user` (Super Admins):** Allowed to run read-only `SELECT` queries across all tenants' rows for rollup dashboards. All write operations (insert, update, delete) are blocked.

---

### Application-Level Scoping (Developer Rules)

To ensure clean querying and performance, developers must follow these rules:
1. **Middleware Role Selection:** The API middleware reads the user's JWT, extracts their role/tenant ID, and chooses the corresponding database connection role (`app_tenant_user` or `app_studio_user`).
2. **ORM Default Scope:** All tenant-scoped models must use a default scope that automatically appends `WHERE tenant_id = ?` to standard queries.
3. **Transaction Safety:** Always use transaction-scoped variables (`SET LOCAL`) so the tenant context is automatically cleared when the database connection is returned to the connection pool (compatible with PgBouncer).

---

## 3. Outbound Scoping & Context Boundaries

*   **Decision:** Segment outbound email workflows strictly by lead/prospect lifecycle stages:
    1. **Pre-MQL (Rules-based & Static Templates):** Triggered sequences of static template emails separated by configurable day gaps. Automatically stops upon reply or status change.
    2. **MQL (AI-Assisted Drafts with Human Review):** Automated draft generation using LLMs. Context injected includes events, company metadata, and sequence history. All emails must sit in an approval queue for manual verification before sending.
       * *Note on MQL Triggers:* In V1, AI sequences are triggered **only** by stage promotion (`mql_promoted`). Triggering sequences off subsequent interactions (`mql_event`) is deferred to V2, as it introduces severe edge cases regarding parallel enrollments, pauses, and racing states if a sequence is already active.
    3. **SQL/Deals (Manual Only):** Zero automated messaging. Sales reps write every email manually to protect customer relationships.
*   **Why this approach:** Protects unit economics (avoiding unnecessary LLM usage on raw leads), guards against AI hallucinations during key mid-funnel touchpoints, and preserves high-touch relationships for active deals.
*   **Unsubscribe Handling (V1 vs V2):**
    *   **V1:** CRM delegates unsubscribe enforcement entirely to the ESP (e.g., SendGrid). The ESP maintains its own suppression list and silently drops sends to unsubscribed addresses at the delivery layer. No CRM-level unsubscribe flag or ESP webhook integration is required in V1.
    *   **V2:** CRM will track unsubscribe events from the ESP webhook. On receipt, the CRM will mark the lead with an `unsubscribed` flag and immediately cancel any active sequence enrollment. This eliminates wasted queue jobs, gives sales reps visibility into opt-out status, and decouples unsubscribe state from any specific ESP (portability).
*   **Notification System (V1 vs V2):**
    *   **V1 (Ignored):** All automated alerts and notifications—such as notifying sales reps when a new lead is added/assigned or when a new AI-generated outbound email draft is pending approval—are ignored to simplify V1 scope. Users must check their respective queues and tables manually in the UI.
    *   **V2:** Implement in-app notifications, email notifications, and webhook integrations (e.g., Slack) to alert reps immediately when a lead is captured or a draft requires review.

---

## 4. AI Security & Tool Boundaries

* **Row-Level Security (RLS) for AI Tools:** To ensure absolute tenant isolation, the AI Worker executing function calls (e.g., `get_lead_history`) MUST initialize its database connection session with the active tenant's context role (`app_tenant_user`). This database-level guarantee prevents the LLM from inadvertently accessing or leaking another tenant's data, regardless of prompt hallucinations.
* **LLM Data Privacy:** To protect proprietary CRM data from model training ingestion, the deployment should utilize a self-hosted private LLM (e.g. vLLM/Ollama in a VPC) or Enterprise APIs (AWS Bedrock, OpenAI Enterprise) covered under strict BAA no-training clauses.
