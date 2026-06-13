# Venture-Studio CRM (Multi-Tenant Growth Engine)

This repository implements the **Lead Scoring and Qualification** slice from the Venture-Studio CRM work trial. The platform is designed to serve multiple startups under one studio, providing event-driven lead lifecycle tracking, automated outbound triggers, and marketing attribution dashboards, all while enforcing absolute multi-tenant data isolation.

To understand the core CRM domain concepts and the terminologies used for B2B SaaS tracking (such as Leads, Accounts, Contacts, Deals, and the conversion lifecycle), please refer to the **[Domain Knowledge Doc](documentations/domain/domain-knowledge.md)**.

---

## 📖 Documentation Directory

### 🏆 Required Deliverables
* **[Systems Design Document (SYSTEMS_DESIGN.md)](SYSTEMS_DESIGN.md):** The primary required systems design document summarizing architecture diagrams, data models, RLS context isolation, trade-offs, and scaling limits.
* **[AI Build Log Summary](transcripts/AI_BUILD_LOG_SUMMARY.md):** Detailed retrospective on the human-AI collaborative process, including rules enforcement (`AGENTS.md`) and course corrections.

### 1. Product & Domain Specs
* **[Domain Knowledge](documentations/domain/domain-knowledge.md):** Glossary of CRM entities and lifecycle flow.
* **[Product Requirements Document (PRD)](documentations/product/prd.md):** Complete requirements, scale assumptions, release phases, and functional scenarios.
* **[Problem Breakdown](documentations/product/problem-breakdown.txt):** Core subproblems mapped to Tenant-Level vs. Studio-Level scopes.

### 2. Architecture & Design
* **[System Architecture](documentations/architecture/architecture.md):** High-level container diagram, webhook data pipeline, and scaling thresholds.
* **[Data Model & ER Diagram](documentations/architecture/data-model.md):** SQL schema details and Mermaid Entity-Relationship diagram.
* **[User Flows & Sequences](documentations/architecture/user-flows.md):** Mermaid sequence diagrams for studio bootstrapping, onboarding, scoring, and outbound triggers.

### 3. Decisions & Implementation Plan
* **[Design Decisions](documentations/decisions/decisions.md):** Core architectural choices (PostgreSQL RLS database design, PgBouncer transaction scopes, RBAC models).
* **[Lead Scoring Implementation Plan](documentations/product/lead-scoring-implementation-plan.md):** Scope boundaries, seed data design, core APIs, and worker mocks for this working submodule prototype.
* **[Lead Scoring Rule Contracts](documentations/architecture/lead-scoring-rule-contracts.md):** Rule contract specifications, JSONB schemas, operators, and validation criteria.
* **[Lead Scoring Prototype Decisions](documentations/decisions/lead-scoring-prototype-decisions.md):** Implementation-specific decisions for the working API prototype (e.g. mocked PostHog events, open property filters).

---

## 🏗️ Implemented Submodule: Lead Scoring & Qualification

We have implemented the **Lead Scoring and Qualification Engine** slice of the CRM. In B2B sales pipelines, this engine serves to automate lead qualification and prioritization. When managing hundreds of leads, startup tenants can rely on defined rules to automatically categorize leads, rather than manually checking each profile and user interaction.

### Why This Matters in a Real CRM Scenario:
*   **Sales Representative Guidance**: Reps need to instantly see the marketing/sales stage of each lead (e.g., Pre-MQL, MQL, SQL) to prioritize their daily tasks and outreach.
*   **Automated Outbounds**: The outbound automation campaigns depend directly on the lead stage. For example, a Pre-MQL lead is enrolled in a standard email sequence, whereas promotion to MQL swaps them to highly personalized AI-assisted drafts.

### Production vs. Prototype Scope:
*   **PostHog Event Tracking**: In production, event aggregates are retrieved from a live PostHog integration. In this prototype, events are mock-stored inside the local database to demonstrate the scoring calculations.
*   **Rules Customization**: Both fit (firmographic) and behavioral scoring rules are dynamically configurable per-tenant.

### Key System Components Implemented:
*   **Rule CRUD Operations**: Full API endpoints allowing a tenant to create, list, update, and delete scoring rules.
*   **Validation Layer**: Sanitizes and enforces schema correctness on tenant-defined rules before database persistence.
*   **Rule Contract Layer**: Exposes versioned rule contract schemas (supported fields, operators, and JSON structures) to the application/UI layer.
*   **Scoring Engine**: Runs multi-tenant scoring queries, evaluating fit and behavioral criteria against active leads.
*   **Trigger Model (CTA Endpoint)**: In a real system, scoring is computed via a nightly batch cron job, supplemented by manual Call-To-Action (CTA) triggers. This prototype implements the tenant-specific CTA endpoint (`/scoring/compute`) to immediately compute and persist scores for all active leads of a tenant.

---

## 🛠️ Prerequisites
To run and test this system locally, you only need:
* **Docker** & **Docker Compose** installed and running on your machine.
* A REST client like **Postman**, **cURL**, or simply the built-in **Swagger UI** (accessed via browser).

---

## 🚀 Setup Flow

1. **Navigate into the `app/` folder:**
   ```bash
   cd app
   ```
2. **Create a `.env` file** to configure the database credentials:
   ```bash
   cp .env.example .env
   ```
3. **Spin up the Docker containers**:
   ```bash
   docker compose down -v
   docker compose up --build -d
   ```
   *Note: This spins up a PostgreSQL database and a FastAPI backend (`http://localhost:8000`). The database is automatically seeded with tenants, leads, scoring rules, and mock PostHog behavioral events via [seed.sql](app/db/seed.sql).*

4. **Verify the API is running**:
   Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to access the interactive Swagger API documentation.

---

## 🔍 Test Flow Walkthrough

This guide walks you through verifying the Lead Scoring & Qualification engine. For these examples, we will use the pre-seeded tenant **Acme SaaS** (Tenant ID: `37e8d336-9d56-49e0-a918-6e555295cee9`).

### Step 1: Inspect Seeded Leads
Before triggering any scoring run, let's fetch the initial state of the leads for Acme SaaS.

* **Endpoint:** `GET http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/leads`
* **cURL Command:**
  ```bash
  curl -X GET http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/leads
  ```
* **Expected Result:**
  Observe the leads returned. For example, **Alice Carter** (`alice@northwind.ai`) has an initial `score` of `0` and a `stage` of `pre_mql`.

---

### Step 2: Trigger Scoring Computation
Let's force the Scoring Engine to run a computation. It will evaluate all active leads for the tenant against their fit rules (firmographic data) and behavioral rules (Mock PostHog event logs stored in the DB).

* **Endpoint:** `POST http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/scoring/compute`
* **cURL Command:**
  ```bash
  curl -X POST http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/scoring/compute
  ```
* **Expected Response:**
  ```json
  {
    "tenant_id": "37e8d336-9d56-49e0-a918-6e555295cee9",
    "processed_lead_count": 3,
    "skipped_lead_count": 1,
    "stage_transition_count": 1,
    "max_possible_score": 85,
    "results": [
      {
        "lead_id": "4b49bb63-b93f-4381-be55-5e1bfb0b1cf7",
        "status": "active",
        "previous_score": 0,
        "raw_score": 55,
        "final_score": 55,
        "previous_stage": "pre_mql",
        "new_stage": "mql",
        "is_stage_manually_overridden": false,
        "matched_rule_names": ["Mid Market Company Size", "SaaS ICP", "Pricing Page Intent"]
      },
      ...
    ]
  }
  ```
* **Adjudication Breakdown:**
  * **Alice Carter** (`4b49bb63-b93f-4381-be55-5e1bfb0b1cf7`) matched:
    * `SaaS ICP` (Fit Rule: industry is SaaS/Fintech) $\rightarrow$ **+20**
    * `Mid Market Company Size` (Fit Rule: size $\ge$ 200) $\rightarrow$ **+15**
    * `Pricing Page Intent` (Behavioral Rule: $\ge$ 2 pricing views in last 30 days) $\rightarrow$ **+20**
    * **Total Score:** `55`. Since this crossed the tenant MQL threshold of `40`, Alice's stage transitioned to **`mql`**!
  * **Cara Mills** (`disqualified` status) was correctly skipped.
  * **Derek Hall** (`is_stage_manually_overridden: true`) had his score updated but his stage was locked at `sql`, protecting his manual qualification assignment.

---

### Step 3: Fetch Updated Lead Record
To verify that the database transaction successfully persisted the results, fetch Alice's lead record.

* **Endpoint:** `GET http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/leads/4b49bb63-b93f-4381-be55-5e1bfb0b1cf7`
* **cURL Command:**
  ```bash
  curl -X GET http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/leads/4b49bb63-b93f-4381-be55-5e1bfb0b1cf7
  ```
* **Expected Response:**
  ```json
  {
    "id": "4b49bb63-b93f-4381-be55-5e1bfb0b1cf7",
    "tenant_id": "37e8d336-9d56-49e0-a918-6e555295cee9",
    "name": "Alice Carter",
    "email": "alice@northwind.ai",
    "status": "active",
    "stage": "mql",
    "score": 55,
    "is_stage_manually_overridden": false,
    ...
  }
  ```

---

### Step 4: Adjust Tenant Scoring Thresholds
A tenant can adjust their scoring thresholds dynamically. Let's raise the MQL threshold to `60` points, making the qualification criteria stricter.

* **Endpoint:** `PUT http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/scoring-thresholds`
* **cURL Command:**
  ```bash
  curl -X PUT http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/scoring-thresholds \
    -H "Content-Type: application/json" \
    -d '{
      "mql_score_threshold": 60,
      "sql_score_threshold": 80
    }'
  ```
* **Expected Response:**
  ```json
  {
    "id": "37e8d336-9d56-49e0-a918-6e555295cee9",
    "name": "Acme SaaS",
    "mql_score_threshold": 60,
    "sql_score_threshold": 80,
    ...
  }
  ```

---

### Step 5: Re-Trigger Compute to Verify Demotion
Now that the threshold has been increased to 60, re-running the scoring computation should demote Alice Carter (score 55) back to `pre_mql`.

* **Endpoint:** `POST http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/scoring/compute`
* **cURL Command:**
  ```bash
  curl -X POST http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/scoring/compute
  ```
* **Expected Result:**
  Check the response body. Alice Carter's `new_stage` is updated back to **`pre_mql`** because her score of `55` is below the new `60` point threshold.

---

### Step 6: Query Available Rule Contracts
To add a new rule, we can inspect versioned rule contract schemas to see the fields, allowed operators, and expected JSON structures.

* **Endpoint:** `GET http://localhost:8000/api/core/scoring-rule-contracts`
* **cURL Command:**
  ```bash
  curl -X GET http://localhost:8000/api/core/scoring-rule-contracts
  ```
* **Expected Result:**
  An array of available fit and behavioral contract schemas.

---

### Step 7: Create a New Fit Scoring Rule
Let's create a new rule to grant **+10** points if the lead has the title "Founder". This will boost Alice's score.

* **Endpoint:** `POST http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/scoring-rules`
* **cURL Command:**
  ```bash
  curl -X POST http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/scoring-rules \
    -H "Content-Type: application/json" \
    -d '{
      "rule_name": "Founder Premium",
      "rule_type": "fit",
      "score_delta": 10,
      "is_active": true,
      "rule_config": {
        "version": 1,
        "field": "title",
        "operator": "equals",
        "value": "Founder"
      }
    }'
  ```
* **Expected Response:**
  A `201 Created` payload containing the newly created rule ID.

---

### Step 8: Final Compute to Verify Re-Promotion
Let's run computation once more. Alice Carter should now match the new `Founder Premium` rule (+10), raising her total score to `65`, crossing the MQL threshold of `60`, and promoting her back to `mql`!

* **Endpoint:** `POST http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/scoring/compute`
* **cURL Command:**
  ```bash
  curl -X POST http://localhost:8000/api/core/tenants/37e8d336-9d56-49e0-a918-6e555295cee9/scoring/compute
  ```
* **Expected Result:**
  Alice Carter's `new_stage` transitions back to **`mql`** with a final score of **`65`**!

---

## 🧪 Running the Automated Test Suite

To verify the complete Lead Scoring services, validation layer, database models, and route configurations:

1. **Run tests on host machine** (requires python virtual env with dependencies installed):
   ```bash
   cd app
   pytest
   ```
2. **Expected Output:** All 29 tests passed successfully (covering fit scorer evaluations, behavioral event groupings, validation rules schemas, and core REST routes).
