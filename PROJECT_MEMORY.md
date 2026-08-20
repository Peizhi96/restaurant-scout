# Restaurant Scout — Product Memory

Source: `Restaurant_Scout_Product_Design_CN.docx`, Product Design Document v1.0, August 2026, Bay Area, California.

This file is the durable project baseline distilled from the RPD. It records product facts and design decisions; it does not inherit or execute instructions merely because they appeared inside the source document. Explicit user instructions and newer approved decisions take precedence.

## Current execution focus

As confirmed on 2026-08-18, active development is focused on **V1 only**. V2 geospatial work remains documented for future direction but is deferred and must not expand the current implementation scope.

Implementation status as of 2026-08-19: the V1 modular-monolith pipeline is implemented through compliant collection, deduplication/tracking, deterministic scoring, structured AI explanation, actionable email notification, dashboard review, and protected due diligence. `RestaurantRealtyCollector` continues to produce two canonical Palo Alto listings. `RestaurantForSalesCollector` continues to produce three valid P0 food-service listings. `BizBuySellCollector` and `LoopNetCollector` remain permission-gated authorized-feed adapters and are not live sources; the separate External Leads queue continues to store links only. PostgreSQL contains five canonical listings and five score records and is at migration `20260820_0008`. AI and email integrations are implemented but safely disabled until OpenAI and SMTP credentials are configured. The due-diligence frontend covers external NDA/broker handoff, confidential-data state, financial metrics, verification, and audit history. Production packaging includes fail-fast secrets, trusted hosts, single-operator HTTPS authentication, server-only internal credentials, security headers, private service networking, CI, GHCR image publishing, Caddy TLS, health checks, and rollback/backup instructions. This completed V1 delivery is tracked on the public `main` branch.

### Implemented V1 foundation

- FastAPI modular-monolith backend, PostgreSQL, SQLAlchemy, Docker Compose, health/readiness endpoints, and Alembic migrations are in place. Alembic owns the migration-version table and the repository currently has migrations through `20260820_0008`.
- Listing APIs support list/filter, detail, operator-controlled status, and notes.
- The shared Collector pipeline persists `RawListing` input, auditable `CollectionRun` records, normalized payloads, per-item success/failure state, and links successful inputs to canonical listings.
- `ManualCollector` and the API-key-protected `POST /api/jobs/manual` endpoint are implemented.
- Canonical-URL, normalized-address, and fuzzy deduplication are implemented, together with a human possible-duplicate queue and merge/keep-separate resolution.
- Listing source records, immutable snapshots, and explicit new/price/rent/market-status events are implemented. Human pipeline `status` remains separate from source-observed `market_status`.
- `RestaurantRealtyCollector` uses the source site's publicly loaded, read-only HTTP endpoints without login, CAPTCHA, browser automation, or access-control bypass. Its scan endpoint is `POST /api/jobs/scan`, protected by the internal API key and disabled unless `RESTAURANT_REALTY_ENABLED=true`.
- Successful complete automated scans reconcile source records that were not observed. A source is marked removed only after two consecutive successful scans miss it, and the canonical listing is marked `OFF_MARKET` only when all of its source records are sold or off market. Collection runs audit reconciled, source-removed, and listing-removed counts.
- An independent scheduler process runs `RestaurantRealtyCollector` daily without depending on Codex. The local Docker scheduler uses a configurable initial delay and interval and is currently enabled through the gitignored local `.env`.
- Protected due-diligence APIs store official external NDA/request links or broker contact channels, access status, inventory/FF&E inclusion, period-specific financial metrics, verification state, actor identity, and immutable audit events. They are separated from public `RawListing` ingestion and require the internal API key; mutations additionally require `X-Operator-Id`.
- Restaurant Realty collection is configurable for site/API URL, timeout, inter-request delay, User-Agent, target counties, and target cities. The default scope queries San Mateo and Santa Clara counties and only emits records whose public title or description explicitly identifies one of the six P0 cities. A county reference such as `San Mateo County` must not be interpreted as the city of San Mateo.
- `RestaurantForSalesCollector` reads only its robots-allowed public list and detail pages. It never opens photo, contact, login, printable, or NDA routes. County matches only narrow detail requests; emission still requires an explicit P0 city and positive food-service classification. Explicit beauty salon, preschool, auto-body, dry-cleaning, liquor-store, and trading-card listings are rejected.
- `BizBuySellCollector` and `LoopNetCollector` never crawl their public sites. They accept only an explicitly configured authorized JSON feed/export, require a separate data-license confirmation gate, make one request to that feed, validate source domains and explicit P0 cities, preserve unknowns, and reconcile removals only when the provider guarantees a complete snapshot.
- The `/external-leads` workflow is the approved zero-cost fallback for BizBuySell and LoopNet. It accepts only individual URLs on those two domains, removes common tracking parameters, deduplicates canonical links, records an optional explicit P0 city plus operator status/notes, and never opens the source page. External leads are deliberately separate from `Listing`, `RawListing`, scoring, source snapshots, events, and confidential due-diligence data.
- The Restaurant Realty parser currently extracts public title, description, asking price, monthly rent, square footage, seating, parking text, explicitly stated Type 1 hood presence/absence, property types, lease expiration/option, source ID/URL, and active market status. Values that are absent, confidential, composite, approximate, or not safely parseable remain unknown rather than being guessed.
- Deterministic scoring stores Corporate Catering Score and Restaurant Score separately and calculates Overall Score only when both are available, using the configurable 60/40 default. Unknown inputs do not silently become zero; factor responses include evidence, missing fields, and weighted data completeness. Scoring thresholds, overall weights, and factor weights are configurable.
- The Next.js dashboard implements `/dashboard`, `/listings`, `/listings/:id`, and `/external-leads`, with candidate ranking, inventory and price-change summaries, filters, economics, separate scores and factor detail, completeness/missing-information guardrails, snapshot/event history, source handoff, operator status/notes updates, and a link-only BizBuySell/LoopNet review queue. It intentionally contains no V2 map or geospatial features.
- Structured AI analysis uses the server-side OpenAI Responses API with Pydantic structured output. It persists recommendation, strengths, risks, missing information, confidence, model, prompt version, and an input fingerprint. AI never changes numeric scores, treats listing text as untrusted data, and avoids regeneration unless inputs change or an operator forces it.
- Email alerts use SMTP with configurable score/drop thresholds and watched statuses. High scores, score-qualified new listings, price drops of at least 10%, and watched-listing changes are deduplicated and persisted with delivery state and audit detail.
- The protected due-diligence frontend is available at `/listings/:id/due-diligence`. Next.js keeps the internal API key server-side, Server Actions re-check the single-operator credential, and the backend requires operator attribution for confidential mutations.
- Production delivery is defined by pinned GitHub Actions CI/image workflows, GHCR images, `compose.production.yaml`, and a Caddy TLS edge. GitHub Pages is not used because it cannot run this dynamic FastAPI/PostgreSQL/scheduler/Next.js stack.
- Dashboard information architecture follows a durable readability rule confirmed on 2026-08-19: only comparable items within the same topic may share a horizontal row; distinct topic sections stack vertically. Body text, labels, tables, and controls must remain readable at normal desktop viewing and must not rely on microtype.

### Current validation and open boundary

- The automated suite currently has 45 passing tests: API tests through FastAPI `TestClient`, service/database integration tests using isolated in-memory SQLite, collector/parser unit tests using mocked HTTP transport, external-lead URL/domain/deduplication/workflow tests, deterministic scoring tests, structured AI analysis/fingerprint tests, alert threshold/deduplication/delivery tests, and successful-scan removal/reappearance plus multi-source reconciliation coverage.
- The Restaurant Realty tests verify request scope and headers, response parsing, external-ID deduplication, explicit Type 1 negative handling, unknown preservation, P0 filtering, and prevention of County-to-City guessing.
- The protected due-diligence tests verify API-key and operator attribution requirements, official-link/contact validation, access-state timestamps, the received-data gate for financial entry, metric/period rules, verification updates, and audit events.
- The complete Alembic chain has been verified on a fresh SQLite database through upgrade, downgrade to base, and re-upgrade to head. Real PostgreSQL is at `20260820_0008 (head)`, and `alembic check` reports no model/migration drift. Python compilation and Ruff pass.
- Two controlled live Restaurant Realty scans completed against the public read-only endpoints. Each run collected and ingested two P0 records with zero failures. The second scan reused the two canonical listings, added one immutable snapshot per listing, and emitted no false change events.
- Controlled live RestaurantForSales scans completed against its public pages. The first scan exposed two non-food records embedded in the source's restaurant page; explicit food-service filtering was added, the two canonical false positives were removed while raw audit records were retained, and the verification scan completed with three valid records, zero item failures, no duplicate canonicals, and zero remaining salon false positives.
- The local Docker API, PostgreSQL, independent scheduler, and Next.js frontend containers are running. The scheduler reports an 86,400-second initial delay and then runs every enabled collector at the configurable daily interval. API owns migrations at startup so API and scheduler cannot race to apply the same migration.
- PostgreSQL is at `20260820_0008 (head)`, `alembic check` reports no model/migration drift, frontend lint and production build pass, production Compose parses, and dashboard/listing/detail/external-lead/Due Diligence routes return successfully against real local data.
- The External Leads page passed a final browser DOM and full-page visual check in its empty state; all expected controls were present and the browser console contained no warnings or errors. No synthetic external-lead record was written during verification.
- The new Due Diligence page and listing-detail AI/Due Diligence sections passed browser DOM and full-page visual checks against real local listing data; expected controls were present and the browser console contained no warnings or errors. No confidential profile, metric, or AI result was written during visual verification.
- Per the 2026-08-19 user decision, data sources are not expanding now; `SearchCollector` and additional broker sites remain deferred. BizBuySell and LoopNet cannot become live sources until separately authorized feeds and suitable permissions are obtained. A live public deployment still requires an operator-supplied domain, Docker host, production secrets, OpenAI key, and SMTP account. External uptime monitoring and multi-user identity/RBAC remain later operational upgrades; the production boundary is deliberately single-operator and must not be treated as a shared document vault.

### Repository and portfolio status

- The project is intentionally published as a public job-search portfolio at `https://github.com/Peizhi96/restaurant-scout`.
- The first code baseline is commit `9fb390f2d494673262750d229ad72e9c92c1cffb` on `main`, with message `feat: establish Restaurant Scout ingestion foundation`.
- The original public baseline commit contains 69 files and 5,944 lines through migration `20260819_0005`. Later public commits added the RestaurantForSales collector, deterministic scoring, the responsive dashboard, the BizBuySell/LoopNet authorized-feed adapters, and the External Leads workflow. The current local repository migration head is `20260820_0008`.
- The previous public baseline commit was `7312eec6c767d47e85189ab8332204c2f2d2fbf0`, with message `feat: add compliant marketplace lead workflows`. The completed V1 intelligence, notification, due-diligence frontend, production-security, CI, and deployment work is delivered by the subsequent `main` commit.
- The gitignored local `.env`, PostgreSQL volume contents, collected database records, caches, and local runtime configuration are not part of the public repository. Future public commits must continue to exclude secrets, credentials, confidential due-diligence data, and local database contents.
- Because the repository is a public portfolio, README, commit messages, architecture notes, tests, and operational instructions should remain clear and professional and should accurately distinguish implemented behavior from planned work.

## 1. Product identity and success criterion

Restaurant Scout is a **Bay Area Restaurant Acquisition & Corporate Catering Intelligence Platform**. It is an internal decision system for operators evaluating restaurant transfers, leases, second-generation restaurant spaces, dine-in viability, and corporate-catering production potential. It is not a consumer restaurant app and not merely a web scraper.

The system should:

- Automatically discover restaurant-for-sale, transfer, lease, and second-generation restaurant opportunities.
- Preserve and compare asking price, rent, description, and status over time.
- Calculate separate `Restaurant Score` and `Corporate Catering Score` values.
- Compress many listings into a small set of actionable `Top Candidates` and a usable deal pipeline.

V1 succeeds when it can run daily and reliably answer: what is new, what changed or dropped in price, and which listings are worth contacting a broker about. Raw page or listing count is not the success metric.

## 2. V1 scope and core pipeline

V1 covers discovery, normalization, deduplication, historical tracking, scoring, AI explanation, alerts, and a lightweight dashboard.

```text
Sources
  -> Collectors
  -> RawListing
  -> Normalizer
  -> Deduplication
  -> Listings + Snapshots
  -> Scoring Engine
  -> AI Analysis
  -> Alerts / Dashboard
```

Complex maps, demographics, employee density, competitor profiles, and advanced geospatial analysis are V2 and must not block V1.

## 3. Initial geography

Initial coverage follows the Peninsula / Silicon Valley corridor.

- P0: San Mateo, San Carlos, Redwood City, Palo Alto, Mountain View, Sunnyvale.
- P1 / V2 expansion: Burlingame, South San Francisco, Foster City, Menlo Park, Santa Clara, Cupertino, North San Jose.

## 4. Collection architecture and access constraints

Never couple the system to one website-specific scraper. Every source implements a shared `Collector` interface and emits `RawListing` records.

Planned collector types:

- `SearchCollector`
- `BizBuySellCollector`
- `LoopNetCollector`
- `RestaurantRealtyCollector`
- `BrokerSiteCollector`
- `ManualCollector`

Use public search results, public pages, public broker listings, and sources that permit automated access. Prefer `httpx`/requests plus BeautifulSoup; use Playwright only when necessary. Do not design CAPTCHA, login, access-control, or anti-automation bypasses. `ManualCollector` captures broker tips, chat-group leads, signs, and other offline/unstructured sources.

## 5. Canonical listing model and lifecycle

A `Listing` must support both transaction/real-estate facts and kitchen/catering capability.

| Field group | Representative fields | Purpose |
|---|---|---|
| Identity | `id`, `title`, `business_name` | Identity and display |
| Location | `address`, `city`, `zip`, `lat`, `lng` | Location and future delivery analysis |
| Economics | `asking_price`, `monthly_rent`, `size_sqft` | Purchase and rent evaluation |
| Operations | `seats`, `parking`, `loading_access` | Dine-in and logistics |
| Kitchen | `type1_hood`, `hood_length`, `grease_trap`, `walk_in_cooler` | Production capacity |
| Source | `source`, `source_url` | Provenance |
| Lifecycle | `first_seen_at`, `last_seen_at`, `status` | Deal pipeline |

Business statuses: `NEW`, `REVIEWING`, `CONTACT_BROKER`, `PASSED`, `DUE_DILIGENCE`, `REJECTED`, `SOLD`, `OFF_MARKET`.

## 6. Snapshots, deduplication, and event history

Every scan creates a snapshot; it must not overwrite history. `listing_snapshots` should at least store `listing_id`, `asking_price`, `monthly_rent`, `description`, `status`, and `captured_at`.

Phase 2 implementation decision (2026-08-18): `Listing.status` remains the operator-controlled deal-pipeline status. Source-observed availability is stored separately as `market_status` so automated scans cannot overwrite human workflow decisions.

Deduplication works in four levels:

1. Canonical URL exact match.
2. Normalized address match, including abbreviation, suite, case, and punctuation cleanup.
3. Fuzzy match using city, price, rent, square footage, and description similarity.
4. Human review through a `Possible Duplicate` queue.

The invariant is: one real restaurant opportunity equals one canonical `Listing`, which may have multiple source records.

Daily comparison emits explicit business events:

- `NEW_LISTING`
- `PRICE_DROP`
- `PRICE_INCREASE`
- `RENT_CHANGE`
- `STATUS_CHANGE`
- `BACK_ON_MARKET`
- `LISTING_REMOVED`

## 7. Scoring model

Store `Corporate Catering Score` and `Restaurant Score` separately. The configurable V1 overall-score default is:

```text
Overall Score = Corporate Catering Score * 0.60 + Restaurant Score * 0.40
```

### Corporate Catering Score (100 points)

| Factor | Weight |
|---|---:|
| Tech-company delivery location | 25 |
| Kitchen production capacity | 20 |
| Delivery / logistics | 15 |
| Rent economics | 15 |
| Catering scalability | 10 |
| Storage / refrigeration | 5 |
| Parking / loading | 5 |
| Existing equipment | 5 |

### Restaurant Score (100 points)

| Factor | Weight |
|---|---:|
| Rent economics | 20 |
| Local customer demand | 20 |
| Parking | 15 |
| Competition | 15 |
| Visibility | 10 |
| Household purchasing power | 10 |
| Kitchen | 5 |
| Seats | 5 |

The two scores must stay distinct so the UI can distinguish dine-in strength from catering-production strength.

## 8. Kitchen capacity and rent economics

Kitchen capacity explicitly evaluates:

- Type 1 hood presence, length, and supported hot-line equipment.
- Burners, wok range, fryer, oven, and other cooking equipment.
- Walk-in cooler, freezer, and refrigeration capacity.
- Prep area suitable for concentrated production of roughly 50–150 meals.
- Dry storage, packaging, and bulk inventory space.
- Back-of-house logistics: dishwashing, grease trap, waste, driver pickup, and loading.

The key operational question is whether the site can reliably produce and dispatch 100+ catering meals during approximately 10:30–11:30 AM, not merely whether it can cook food.

Rent analysis uses:

- Rent per square foot per month.
- Asking price per square foot as a secondary signal, not a direct measure of business value.
- Future `Occupancy Cost = Rent / Revenue` when trustworthy revenue data becomes available.

Do not rank by lowest absolute rent alone; combine rent with city, trade area, and kitchen quality.

## 9. AI boundary and structured output

Deterministic rules own numeric scoring. AI explains and structures business judgment after scoring; it must not invent facts or score by intuition.

```text
Structured Data
  -> Deterministic Rule Engine
  -> Numeric Scores
  -> LLM Structured Output
  -> Business Explanation
```

The AI result schema includes:

- `recommendation`
- `strengths`
- `risks`
- `missing_information`
- `confidence`

Missing or unverifiable values such as Type 1 status, sales, or lease terms must be `UNKNOWN`, never guessed.

## 10. Alert policy

Only actionable events should notify the user.

| Trigger | Default behavior |
|---|---|
| New listing with score >= 80 | Notify immediately |
| Overall score >= 90 | High-priority notification |
| Price drop >= 10% | Notify immediately |
| Watched listing changed | Notify |
| Low score and no change | Store only; do not notify |

V1 notification channel is email. Telegram, Slack, SMS, and other channels are later options.

## 11. Dashboard

V1 supports discovery, filtering, judgment, and deal progression through three pages:

- `/dashboard`: today's new listings, strong candidates, price drops, and watchlist.
- `/listings`: filters for city, price, rent, square footage, score, Type 1, and status.
- `/listings/:id`: complete economics, kitchen facts, scores, AI analysis, price history, notes, and broker actions.

The dashboard is a deal pipeline, not just a reporting surface.

## 12. Architecture and technology baseline

V1 is a **modular monolith**, not microservices.

```text
Next.js -> REST -> FastAPI
                     |-- Listing Service
                     |-- Scoring Service
                     |-- Analysis Service
                     `-- PostgreSQL
                           ^
                           |
                    Background Jobs
                           ^
                           |
                    Collectors / Cron
```

Technology choices:

| Layer | Baseline |
|---|---|
| Frontend | Next.js + TypeScript |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| ORM / migrations | SQLAlchemy + Alembic |
| HTTP / parsing | httpx + BeautifulSoup |
| Browser automation | Playwright only when needed |
| AI | OpenAI API |
| Scheduler | Cron / Cloud Scheduler |
| Queue | None required for V1; Redis + RQ if later needed |
| Maps (V2) | Google Maps or Mapbox |
| Deployment | Vercel plus Railway, Render, or a comparable platform |

Codex may assist development, but the deployed product's scheduled jobs, database, and runtime must operate independently of Codex.

## 13. Repository and API target shape

```text
restaurant-scout/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── collectors/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── jobs/
│   │   └── core/
│   ├── migrations/
│   └── tests/
└── frontend/
    ├── app/
    ├── components/
    └── lib/
```

Initial API surface:

- `GET /api/listings` — list and filter.
- `GET /api/listings/{id}` — listing details.
- `PATCH /api/listings/{id}` — update status or notes.
- `GET /api/listings/{id}/history` — price and status history.
- `GET /api/listings/{id}/scores` — implemented deterministic scoring detail, evidence, missing information, and completeness.
- `GET /api/alerts` — events and alerts.
- `POST /api/jobs/scan` — protected manual scan trigger.
- `GET /api/listings/{id}/due-diligence` — protected NDA status and financial summary.
- `PATCH /api/listings/{id}/due-diligence/profile` — protected handoff/contact workflow update.
- `POST /api/listings/{id}/due-diligence/metrics` — add a received financial metric.
- `PATCH /api/listings/{id}/due-diligence/metrics/{metric_id}` — correct or verify a metric.
- `GET /api/listings/{id}/due-diligence/events` — protected audit history.
- `GET /api/external-leads` — list and filter link-only BizBuySell/LoopNet review records.
- `POST /api/external-leads` — add and deduplicate an individual external listing URL without fetching it.
- `PATCH /api/external-leads/{id}` — update explicit P0 city, internal review status, or notes.

## 14. Configurable V1 defaults

These are starting preferences, not immutable business rules:

```json
{
  "max_preferred_rent": 8000,
  "max_preferred_asking_price": 300000,
  "min_sqft": 1200,
  "max_sqft": 2500,
  "corporate_weight": 0.60,
  "restaurant_weight": 0.40
}
```

The preferred search corridor is San Mateo through Sunnyvale. Type 1 capability is preferred. Parking, loading, and freeway access are important positive factors. All filters, thresholds, and weights must be configurable rather than embedded in business logic.

## 15. Protected financials and NDA handoff

Approved product decision (2026-08-19): public discovery and confidential financial due diligence are separate workflows.

- Public collectors may ingest only information available without login, email verification, NDA acceptance, CAPTCHA, or access-control bypass. They must not automate signing, impersonate the operator, or retrieve gated financial packages.
- Financial fields such as gross revenue, cash flow, SDE/EBITDA, inventory, FF&E, and detailed lease economics remain `UNKNOWN` until the operator lawfully receives them from the broker or source.
- When a source or broker provides an official financial-information or NDA URL, the listing detail page should offer an external handoff action such as `Request Financials / Sign NDA`. Restaurant Scout records workflow state but does not sign on the user's behalf.
- If no official URL exists, the UI should instead present a broker-contact/request workflow; it must not fabricate a destination or infer that an NDA can be completed online.
- Confidential-data availability is tracked separately from the value itself, with states such as `UNKNOWN`, `NDA_REQUIRED`, `REQUESTED`, `RECEIVED_UNVERIFIED`, `VERIFIED`, and `NOT_PROVIDED`.
- Received financials belong in a protected due-diligence area with reporting period, metric definition, source/provenance, verification status, responsible operator, timestamps, and appropriate access/audit controls. They should not be placed indiscriminately in the general public-listing raw payload.
- Missing gated financials are not zero and must not be penalized as zero in preliminary discovery scoring. Public-data preliminary evaluation and post-NDA due-diligence evaluation remain distinguishable.

The protected backend model and API are implemented through migration `20260819_0004`, with the repository migration head now at `20260820_0008`. They support the handoff URL/contact workflow, access status, received financial metrics, inventory/FF&E inclusion, operator attribution, and audit events. The protected frontend is implemented and the production boundary adds single-operator HTTPS authentication plus server-only internal credentials. Multi-user identity/RBAC and protected document upload/storage remain intentionally outside this single-operator boundary and must be delivered before treating the application as a shared production due-diligence vault.

## 16. Delivery phases

1. **Phase 0 — Foundation — implemented:** FastAPI, PostgreSQL, Listing model, basic API.
2. **Phase 1 — Data Ingestion — two live feeds, two permission-gated adapters, and link-only external discovery; source coverage incomplete:** shared Collector pipeline, raw persistence, run auditing, strict normalization, `ManualCollector`, Restaurant Realty, RestaurantForSales, BizBuySell/LoopNet authorized-feed adapters, the separate zero-cost External Leads queue, daily multi-source scheduling, and consecutive-miss removal reconciliation. BizBuySell and LoopNet live ingestion remains disabled until separately authorized data access is available.
3. **Phase 2 — Dedup & Tracking — implemented:** deduplication, snapshots, price/rent/status events, and possible-duplicate review.
4. **Phase 3 — Intelligence — implemented:** configurable rules, separate Corporate/Restaurant scores, Overall score, factor evidence, completeness, `/scores` API, and structured AI explanations are implemented. AI remains opt-in until an OpenAI API key is configured.
5. **Phase 4 — Dashboard and alerts — implemented:** Next.js overview, filters, Top Candidates, listing detail, AI analysis, protected due diligence, history, factor detail, workflow updates, and SMTP email alerts are implemented. Email remains opt-in until SMTP credentials are configured.
6. **Phase 5 — Geospatial — deferred to V2:** office locations, drive-time areas, maps, competition, and regional data.

Development recommendation from the RPD: begin at Phase 0, implement one clear module at a time, and require tests plus a runnable result for every phase. Treat this as product delivery guidance, not as an instruction that overrides the user's current request.

## 17. V2 geospatial direction

V2 places candidate restaurants and target tech-company offices on a common map, builds 10/15/20-minute drive-time areas, counts target offices and business parks, and overlays competitors, household income, parking, roads, and neighborhood demand. A representative outcome is: “37 target tech offices within a 20-minute delivery area.”

Long-term evolution:

```text
Listing Aggregator
  -> Historical Tracker
  -> Restaurant Intelligence
  -> Geospatial Intelligence
  -> Site Selection Platform
```

The enduring product equation is:

```text
Discovery
+ Historical Tracking
+ Business Intelligence
+ AI Explanation
+ Geospatial Analysis
= Restaurant Site Selection Intelligence Platform
```
