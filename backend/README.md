# portal-nem-backend

Django + DRF core backend for portal_nem. See `../docs/design-brief.md` and
`../openspec/changes/m2a-tenancy-core/` for the tenancy foundation design.

## Setup

```bash
uv sync
uv run python manage.py migrate
uv run pytest
```

Requires PostgreSQL with the `vector` extension available and a `DATABASE_URL`
pointing at it (see `.env.example` at the repo root).
