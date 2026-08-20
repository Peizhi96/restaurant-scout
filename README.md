# Restaurant Scout

Restaurant Scout is a V1-focused internal platform for discovering, tracking, and evaluating Bay Area restaurant acquisition and corporate-catering opportunities.

The current implementation covers the V1 pipeline from compliant collection through tracking, deterministic scoring, structured AI analysis, actionable email alerts, protected due diligence, and production packaging. Manual ingestion, Restaurant Realty, RestaurantForSales, BizBuySell, and LoopNet all use the shared Collector interface. BizBuySell and LoopNet remain disabled until an authorized feed and suitable data permission are supplied; they do not crawl either public website.

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
- A link-only marketplace feed that imports individual BizBuySell URLs from official saved-search email alerts over IMAP, with sender allowlisting, strict listing-path validation, URL deduplication, audit runs, and a secondary manual missed-link fallback. These links remain separate from copied listing facts, scoring, AI, and source-history tracking.
- Daily scheduling independent of Codex.
- Two-consecutive-miss removal reconciliation with source and listing audit counts.
- A protected NDA/broker handoff and financial due-diligence backend and frontend, including access state, period-specific metrics, inventory/FF&E inclusion, verification status, and audit events.
- Configurable deterministic Corporate Catering, Restaurant, and 60/40 Overall scores, including factor evidence, missing information, and data completeness.
- Structured OpenAI analysis that can explain but never replace deterministic scores, with persisted recommendations, strengths, risks, explicit missing information, confidence, model, prompt version, and an input fingerprint that avoids unnecessary regeneration.
- SMTP email alerts for new score-qualified candidates, high-priority candidates, price drops of at least 10%, and changes to watched pipeline statuses. Every attempted alert is deduplicated and audited.
- A responsive Next.js dashboard with overview, filters, listing detail, AI analysis, due diligence, score factors, history, events, and operator status/notes.
- Production fail-fast configuration, single-operator HTTP Basic authentication behind HTTPS, server-only internal credentials, trusted-host enforcement, security headers, private service networking, CI, and GHCR image publishing.

See `PROJECT_MEMORY.md` for the durable product and architecture baseline.

## Run with Docker

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`, with OpenAPI documentation at `http://localhost:8000/docs`.
The dashboard is available at `http://localhost:3001/dashboard`. Port 3001 is the local default and can be changed with `FRONTEND_PORT`.
The link-only marketplace feed is available at `http://localhost:3001/external-leads`.

AI and email remain opt-in locally. Copy the relevant settings from `.env.example`, set
`OPENAI_ENABLED=true` and/or `EMAIL_ENABLED=true`, and provide the required credentials.
Secrets must stay in the gitignored `.env`; never commit API keys, SMTP passwords, or
confidential due-diligence data.

## Configure BizBuySell saved-search links

Restaurant Scout never crawls BizBuySell search or detail pages. Instead, create a
dedicated mailbox or folder, open the official San Mateo County and Santa Clara County
restaurant searches linked from `/external-leads`, and enable BizBuySell's Save Search
email notifications. Configure the mailbox in the gitignored `.env`:

```bash
BIZBUYSELL_EMAIL_ALERTS_ENABLED=true
BIZBUYSELL_IMAP_HOST=imap.example.com
BIZBUYSELL_IMAP_PORT=993
BIZBUYSELL_IMAP_USERNAME=restaurant-scout@example.com
BIZBUYSELL_IMAP_PASSWORD=use-a-provider-specific-app-password
BIZBUYSELL_IMAP_MAILBOX=INBOX
BIZBUYSELL_EMAIL_ALLOWED_SENDER_DOMAINS=bizbuysell.com
```

Use a dedicated mailbox or isolated folder rather than a personal inbox. The scheduler
reads unseen messages from allowed sender domains, extracts only individual
`/business-opportunity/` and `/business-asset/` links, stores no email body, and marks a
valid alert as seen only after processing. Links can also be synced on demand from the
Marketplace link feed. IMAP credentials remain server-side and are never exposed to the
browser or stored in PostgreSQL.

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

By default, the scheduler runs every day at 8:00 AM in `America/Los_Angeles`, following
PDT/PST daylight-saving changes automatically. Container restarts do not shift that
wall-clock schedule. A listing source must be absent from two consecutive successful
complete scans before it is treated as removed. A canonical listing remains available
while any other source still reports it as active or unknown.

Set `RESTAURANT_FOR_SALES_ENABLED=true` to include the public RestaurantForSales feed.
The collector does not open photo, contact, login, or NDA routes. Each enabled source is
reconciled independently.

## Configure permission-gated sources

BizBuySell and LoopNet currently prohibit scraping and database extraction without
express written permission. Restaurant Scout therefore supports only a separately
authorized JSON feed or export for these sources. Review
`docs/SOURCE_FEASIBILITY_AUDIT.md` before configuration.

The BizBuySell saved-search email integration is a separate link-only path: it stores
only hyperlinks BizBuySell sends to the operator and never opens the source page. It
does not enable BizBuySell as a canonical detail collector and does not require
`BIZBUYSELL_ENABLED=true`.

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
- `GET /api/listings/{id}/analysis`
- `POST /api/listings/{id}/analysis/generate`
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
- `GET /api/external-leads/bizbuysell-email/status`
- `POST /api/external-leads/bizbuysell-email/sync`

Job endpoints, AI generation, listing mutations, and external-lead mutations require the `X-Internal-API-Key` header. Set `INTERNAL_API_KEY` to a unique secret of at least 32 characters before production deployment.

Due-diligence endpoints also require `X-Internal-API-Key`; profile and metric mutations additionally require `X-Operator-Id` for audit attribution. The backend stores official external handoff URLs but never signs an NDA, verifies email, or bypasses a source's access controls on the operator's behalf.

## Production deployment

GitHub Pages cannot run this application because it is a dynamic FastAPI/PostgreSQL/
Next.js stack. GitHub Actions and GHCR are used for CI and versioned container images;
the containers run on a Docker host with persistent storage. See
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the release, TLS, backup, rollback, and
post-deployment verification procedure.
