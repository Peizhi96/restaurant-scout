# Production deployment

Restaurant Scout uses GitHub for source control, CI, releases, and container images.
It does not use GitHub Pages: Pages is static hosting and cannot operate the FastAPI,
PostgreSQL, scheduler, or server-rendered Next.js services.

## Topology

```text
Internet -> Caddy (automatic HTTPS) -> Next.js
                                      -> FastAPI (private network)
                                         -> PostgreSQL (private volume)
                                      scheduler -> FastAPI database modules

GitHub release -> Actions -> GHCR API and frontend images -> Docker host
```

Only Caddy publishes host ports. PostgreSQL and FastAPI have no public port in
`compose.production.yaml`. The internal API key and due-diligence data never reach the
browser; Next.js performs protected API calls server-side.

## 1. Publish images from GitHub

1. Merge a validated revision to `main` and create a GitHub release, or manually run
   the `Publish production images` workflow.
2. The workflow publishes `restaurant-scout-api` and
   `restaurant-scout-frontend` to GHCR with both `latest` and immutable commit-SHA tags.
3. Prefer the commit-SHA tag in production after the first deployment so rollback is
   deterministic.

The workflow grants only `contents: read` and `packages: write` and pins third-party
actions to commit SHAs.

## 2. Prepare the Docker host

Use a small Linux VM with Docker Engine, Compose v2, a DNS A/AAAA record, and inbound
TCP 80/443. Copy these repository files to a dedicated application directory:

- `compose.production.yaml`
- `deploy/Caddyfile`
- `deploy/.env.production.example`

Copy the example to `.env.production`, restrict it to the service account, and replace
every placeholder. Generate separate long random values for the PostgreSQL password,
`INTERNAL_API_KEY`, and `APP_AUTH_PASSWORD`. URL-encode the database password inside
`DATABASE_URL`. Enable AI or email only after their required secrets are present.
If BizBuySell saved-search ingestion is enabled, use a dedicated IMAP mailbox or folder
and a provider-specific app password; never reuse the operator's primary email password.

```bash
chmod 600 deploy/.env.production
docker compose --env-file deploy/.env.production -f compose.production.yaml config --quiet
docker compose --env-file deploy/.env.production -f compose.production.yaml pull
docker compose --env-file deploy/.env.production -f compose.production.yaml up -d
```

For private GHCR packages, log in once on the host with a read-only package token. A
public portfolio repository can instead expose the packages publicly.

## 3. Verify

```bash
docker compose --env-file deploy/.env.production -f compose.production.yaml ps
docker compose --env-file deploy/.env.production -f compose.production.yaml logs --tail=100 api frontend scheduler caddy
curl --fail --user 'operator:your-password' https://scout.example.com/dashboard
```

Verify that unauthenticated requests return 401, HTTPS is valid, the API and database
are not reachable on public ports, migrations completed, and the scheduler reports its
next run at 8:00 AM in the configured `America/Los_Angeles` timezone. Then exercise one
non-sensitive listing update and inspect the audit state.

## 4. Backups and rollback

Schedule an encrypted daily `pg_dump` to storage outside the VM and test restoration
regularly. Backups contain confidential due-diligence data and must use access controls
and retention limits appropriate to that data.

Before every upgrade, record the current `IMAGE_TAG` and take a database backup. To
roll back application code, restore the prior immutable image tag and run `up -d`.
Database downgrades are a separate, higher-risk operation; restore a verified backup
instead of blindly downgrading a production schema.

## Security boundary

The included authentication is intended for a single operator. It is safe only behind
HTTPS with a strong unique password. If the application becomes multi-user, replace it
with an identity provider, per-user sessions, role-based access, and per-user audit
identity before granting access. Do not expose this public portfolio deployment as a
shared confidential document vault.
