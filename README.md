# Restaurant Scout

Restaurant Scout is a V1-focused internal platform for discovering, tracking, and evaluating Bay Area restaurant acquisition and corporate-catering opportunities.

The current implementation includes **Phase 0 — Foundation**, two operational **Phase 1 — Data Ingestion** feeds, two permission-gated source adapters, **Phase 2 — Dedup & Tracking**, the deterministic portion of **Phase 3 — Intelligence**, and the V1 dashboard portion of **Phase 4**. Manual ingestion, Restaurant Realty, RestaurantForSales, BizBuySell, and LoopNet all use the shared Collector interface. BizBuySell and LoopNet are disabled until an authorized feed and suitable data permission are supplied; they do not crawl either public website.

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
- A live-validated `RestaurantForSalesCollector` using only public list/detail pages, with strict target-city and food-service filtering.
- Permission-gated `BizBuySellCollector` and `LoopNetCollector` adapters for separately authorized JSON feeds or exports. Their public websites are not crawled.
- A zero-cost, link-only external-lead queue for BizBuySell and LoopNet, with URL deduplication, source recognition, P0 city selection, internal status, and notes. External leads remain separate from copied listing facts, scoring, and source-history tracking.
- Daily scheduling independent of Codex.
- Two-consecutive-miss removal reconciliation with source and listing audit counts.
- A protected NDA/broker handoff and financial due-diligence backend, including access state, period-specific metrics, inventory/FF&E inclusion, verification status, and audit events.
- Configurable deterministic Corporate Catering, Restaurant, and 60/40 Overall scores, including factor evidence, missing information, and data completeness.
- A responsive Next.js dashboard with overview, filters, listing detail, score factors, history, events, and operator status/notes.

See `PROJECT_MEMORY.md` for the durable product and architecture baseline.

## Run with Docker

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`, with OpenAPI documentation at `http://localhost:8000/docs`.
The dashboard is available at `http://localhost:3001/dashboard`. Port 3001 is the local default and can be changed with `FRONTEND_PORT`.
The link-only external-lead queue is available at `http://localhost:3001/external-leads`.

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

Set `RESTAURANT_FOR_SALES_ENABLED=true` to include the public RestaurantForSales feed.
The collector does not open photo, contact, login, or NDA routes. Each enabled source is
reconciled independently.

## Configure permission-gated sources

BizBuySell and LoopNet currently prohibit scraping and database extraction without
express written permission. Restaurant Scout therefore supports only a separately
authorized JSON feed or export for these sources. Review
`docs/SOURCE_FEASIBILITY_AUDIT.md` before configuration.

After obtaining appropriate permission and a compatible feed, configure the relevant
`*_AUTHORIZED_FEED_URL`, optionally configure `*_AUTHORIZED_FEED_TOKEN`, then set both
`*_DATA_LICENSE_CONFIRMED=true` and `*_ENABLED=true`. Keep `*_FEED_IS_COMPLETE=false`
unless every run is guaranteed to be a complete source snapshot.

## Current API

- `GET /healthz`
- `GET /readyz`
- `GET /api/listings`
- `GET /api/listings/{id}`
- `PATCH /api/listings/{id}`
- `GET /api/listings/{id}/history`
- `GET /api/listings/{id}/events`
- `GET /api/listings/{id}/scores`
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
- `GET /api/external-leads`
- `POST /api/external-leads`
- `PATCH /api/external-leads/{id}`

Job endpoints require the `X-Internal-API-Key` header. Set `INTERNAL_API_KEY` to a non-default secret before any non-local deployment.

Due-diligence endpoints also require `X-Internal-API-Key`; profile and metric mutations additionally require `X-Operator-Id` for audit attribution. The backend stores official external handoff URLs but never signs an NDA, verifies email, or bypasses a source's access controls on the operator's behalf.
