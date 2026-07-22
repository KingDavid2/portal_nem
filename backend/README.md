# portal-nem-backend

Django + DRF core backend for portal_nem. See `../docs/design-brief.md` and
`../openspec/changes/archive/m2a-tenancy-core/` for the tenancy foundation design.

## Prerequisites

- **Python 3.13** (pinned in `.python-version`)
- **[uv](https://docs.astral.sh/uv/)** — dependency + venv manager
- **PostgreSQL** with the `vector` (pgvector) extension available. Local dev
  assumes trust auth (e.g. Postgres.app) and a superuser-owned database.

Create the database once:

```bash
createdb portal_nem
```

## Configuration

Settings read from `../.env` (repo root) via `django-environ`. Copy the example
and adjust if your Postgres setup differs from the trust-auth default:

```bash
cp ../.env.example ../.env
```

Relevant variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgres:///portal_nem` | Owner role — runs migrations/DDL |
| `DJANGO_DB_ROLE` | `migrate` | `migrate` = owner; `runtime` = restricted app role |
| `APP_DATABASE_URL` | _(unset)_ | Restricted `portal_app` role, used when `DJANGO_DB_ROLE=runtime` |
| `DJANGO_SECRET_KEY` | insecure dev key | Set a real value outside dev |
| `DEBUG` | `True` | — |

## Setup

```bash
uv sync                              # install deps into .venv
uv run python manage.py migrate      # apply migrations (creates pgvector ext, portal_app role, RLS)
```

Migrations run as the **owner** role (`DJANGO_DB_ROLE=migrate`, the default).
Migration `workspaces/0003_rls` enables row-level security and creates the
restricted `portal_app` runtime role (`NOSUPERUSER NOBYPASSRLS`).

## Run

```bash
uv run python manage.py runserver
```

To exercise the RLS backstop under the restricted role, set an
`APP_DATABASE_URL` pointing at `portal_app` and run with `DJANGO_DB_ROLE=runtime`.

## Test

```bash
uv run pytest                        # full suite (pytest-django)
uv run pytest workspaces/            # one app
uv run pytest -k rls                 # by keyword
uv run python manage.py migrate --check   # fail if models drift from migrations
```

Tests need a reachable Postgres — pytest-django creates and drops a
`test_portal_nem` database, so the configured role must be able to create
databases (the owner role does locally).
