# Restaurant Scout

Restaurant Scout is a V1-focused internal platform for discovering, tracking, and evaluating Bay Area restaurant acquisition and corporate-catering opportunities.

The current implementation includes **Phase 0 — Foundation**, the first operational **Phase 1 — Data Ingestion** feed, and **Phase 2 — Dedup & Tracking**. Manual ingestion and the public read-only Restaurant Realty collector both use the shared Collector interface. The Restaurant Realty feed has completed two controlled live PostgreSQL scans and can run daily through an independent scheduler container.

- FastAPI application and health/readiness endpoints.
- PostgreSQL persistence through SQLAlchemy 2.
- Alembic migration for the canonical `listings` table.
- Listing list/filter, detail, and status/notes update APIs.
- Isolated API tests using an in-memory SQLite database.
- Canonical URL, normalized-address, and fuzzy deduplication.
- Source records, immutable snapshots, change events, and a human duplicate-review queue.
- Persisted raw listings and auditable collection runs.
- Strict business-field normalization with per-item failure isolation.
- `ManualCollector` and an API-key-protected manual import endpoint.
- A live-validated `RestaurantRealtyCollector` and protected automated scan endpoint.
- Daily scheduling independent of Codex.
- Two-consecutive-miss removal reconciliation with source and listing audit counts.
- A protected NDA/broker handoff and financial due-diligence backend, including access state, period-specific metrics, inventory/FF&E inclusion, verification status, and audit events.

See `PROJECT_MEMORY.md` for the durable product and architecture baseline.

## Run with Docker

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`, with OpenAPI documentation at `http://localhost:8000/docs`.

## Run tests locally

From `backend/`, install the development dependencies and run:

```bash
python -m pip install -e '.[dev]'
pytest
```

Or run the reproducible Docker validation target, which executes Ruff and all tests:

```bash
docker compose --profile validation up --build --abort-on-container-exit --exit-code-from test test
```

## Run daily collection

Set `RESTAURANT_REALTY_ENABLED=true` in the gitignored local `.env`, then start the
independent scheduler:

```bash
docker compose --profile scheduler up -d --build scheduler
```

The default interval is 86,400 seconds. A listing source must be absent from two
consecutive successful complete scans before it is treated as removed. A canonical
listing remains available while any other source still reports it as active or unknown.

## Current API

- `GET /healthz`
- `GET /readyz`
- `GET /api/listings`
- `GET /api/listings/{id}`
- `PATCH /api/listings/{id}`
- `GET /api/listings/{id}/history`
- `GET /api/listings/{id}/events`
- `GET /api/possible-duplicates`
- `PATCH /api/possible-duplicates/{id}`
- `POST /api/jobs/manual`
- `POST /api/jobs/scan`
- `GET /api/jobs/runs`
- `GET /api/jobs/runs/{id}`
- `GET /api/jobs/runs/{id}/items`
- `GET /api/listings/{id}/due-diligence`
- `PATCH /api/listings/{id}/due-diligence/profile`
- `POST /api/listings/{id}/due-diligence/metrics`
- `PATCH /api/listings/{id}/due-diligence/metrics/{metric_id}`
- `GET /api/listings/{id}/due-diligence/events`

Job endpoints require the `X-Internal-API-Key` header. Set `INTERNAL_API_KEY` to a non-default secret before any non-local deployment.

Due-diligence endpoints also require `X-Internal-API-Key`; profile and metric mutations additionally require `X-Operator-Id` for audit attribution. The backend stores official external handoff URLs but never signs an NDA, verifies email, or bypasses a source's access controls on the operator's behalf.
