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
