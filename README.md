# Meraki Lead Scoring API

This repository implements the **Lead Scoring and Qualification** slice from the Meraki full stack engineer work trial.

Current status:

- milestone 1 complete
- FastAPI backend bootstrapped
- PostgreSQL schema initialized by the Postgres container
- demo seed data inserted by Postgres init scripts
- health endpoint available

## Run

```bash
cd app
cp .env.example .env
docker compose up --build
```

The runnable FastAPI module lives in `app/`.
The reviewer seed data is created by PostgreSQL during container initialization.

## Inspect Seed Data

There is intentionally no tenant-listing helper endpoint in the API surface. Tenant isolation is central to this slice, so seeded tenant and lead inspection should happen through the seed file or through `psql`.

Seed source:

- [app/db/seed.sql](/Users/shagunarora/work-in-progress/meraki-labs-assignment/app/db/seed.sql)

Open a Postgres shell:

```bash
cd app
docker exec -it meraki_lead_scoring-postgres-1 psql -U meraki -d meraki_lead_scoring
```

Useful queries:

```sql
SELECT id, name, mql_score_threshold, sql_score_threshold
FROM tenants;

SELECT id, tenant_id, name, email, stage, score, status
FROM leads
ORDER BY created_at;

SELECT id, tenant_id, rule_name, rule_type, score_delta, is_active
FROM lead_scoring_rules
ORDER BY created_at;
```

## Verify

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "Meraki Lead Scoring API"
}
```

## Re-seed Demo Data

PostgreSQL init scripts run only when the database volume is created for the first time.

To rebuild the demo database from scratch:

```bash
cd app
docker compose down -v
docker compose up --build
```

Later milestones will add the scoring APIs, helper APIs, and the qualification engine.

## Prototype Decisions

For the lead-scoring slice, some reviewer-facing behavior is intentionally mocked in code for speed:

- Behavioral scoring rule `event_name` validation uses a code-defined mock PostHog event catalog.
- The allowed event names are returned by the scoring-rule contract API, so reviewers can discover them before inserting rules.
- `property_filters` are accepted as open JSON objects in V1; a mocked property catalog is intentionally deferred.

Reference:

- [documentations/decisions/lead-scoring-prototype-decisions.md](/Users/shagunarora/work-in-progress/meraki-labs-assignment/documentations/decisions/lead-scoring-prototype-decisions.md)
