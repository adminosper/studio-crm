# Venture-Studio CRM (Multi-Tenant Growth Engine)

This repository implements the **Lead Scoring and Qualification** slice from the Venture-Studio CRM work trial. The platform is designed to serve multiple startups under one studio, providing event-driven lead lifecycle tracking, automated outbound triggers, and marketing attribution dashboards, all while enforcing absolute multi-tenant data isolation.

To understand the core CRM domain concepts and the terminologies used for B2B SaaS tracking (such as Leads, Accounts, Contacts, Deals, and the conversion lifecycle), please refer to the **[Domain Knowledge Doc](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/domain/domain-knowledge.md)**.

---

## 📖 Documentation Directory

Refer to the following documents for design, architecture, and product decisions:

### 1. Product & Domain Specs
* **[Domain Knowledge](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/domain/domain-knowledge.md):** Glossary of CRM entities and lifecycle flow.
* **[Product Requirements Document (PRD)](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/product/prd.md):** Complete requirements, scale assumptions, release phases, and functional scenarios.
* **[Problem Breakdown](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/product/problem-breakdown.txt):** Core subproblems mapped to Tenant-Level vs. Studio-Level scopes.

### 2. Architecture & Design
* **[System Architecture](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/architecture.md):** High-level container diagram, webhook data pipeline, and scaling thresholds.
* **[Data Model & ER Diagram](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/data-model.md):** SQL schema details and Mermaid Entity-Relationship diagram.
* **[User Flows & Sequences](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/user-flows.md):** Mermaid sequence diagrams for studio bootstrapping, onboarding, scoring, and outbound triggers.

### 3. Decisions & Implementation Plan
* **[Design Decisions](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/decisions/decisions.md):** Core architectural choices (PostgreSQL RLS database design, PgBouncer transaction scopes, RBAC models).
* **[Lead Scoring Implementation Plan](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/product/lead-scoring-implementation-plan.md):** Scope boundaries, seed data design, core APIs, and worker mocks for this working submodule prototype.
* **[Lead Scoring Rule Contracts](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/architecture/lead-scoring-rule-contracts.md):** Rule contract specifications, JSONB schemas, operators, and validation criteria.
* **[Lead Scoring Prototype Decisions](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/decisions/lead-scoring-prototype-decisions.md):** Implementation-specific decisions for the working API prototype (e.g. mocked PostHog events, open property filters).

---

## 🚀 Run the Prototype

The runnable FastAPI backend module lives in `app/`. The PostgreSQL database schema and seed data are initialized automatically during container setup.

```bash
cd app
cp .env.example .env
docker compose up --build
```

---

## 🔍 Inspect Seed Data

Tenant isolation is central to this prototype, so there is intentionally no public "list all tenants" API endpoint. You can inspect the seeded tenant and lead information directly through the seed source or through `psql`.

* **Seed Source file:** [app/db/seed.sql](file:///Users/shagunarora/work-in-progress/meraki-labs-assignment/app/db/seed.sql)

### Open a Postgres Shell
```bash
cd app
docker exec -it meraki_lead_scoring-postgres-1 psql -U meraki -d meraki_lead_scoring
```

### Useful Inspection Queries
```sql
-- View seeded tenants and scoring thresholds
SELECT id, name, mql_score_threshold, sql_score_threshold 
FROM tenants;

-- View seeded leads and their qualification states
SELECT id, tenant_id, name, email, stage, score, status 
FROM leads 
ORDER BY created_at;

-- View seeded scoring rules
SELECT id, tenant_id, rule_name, rule_type, score_delta, is_active 
FROM lead_scoring_rules 
ORDER BY created_at;
```

---

## 🧪 Verify & Re-Seed

### Verify API Health
```bash
curl http://localhost:8000/health
```
**Expected Response:**
```json
{
  "status": "ok",
  "service": "Meraki Lead Scoring API"
}
```

### Re-seed Demo Data
PostgreSQL initialization scripts run only when the database volume is created for the first time. To rebuild and re-seed the database:
```bash
cd app
docker compose down -v
docker compose up --build
```
