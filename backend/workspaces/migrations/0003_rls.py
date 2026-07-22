"""RLS policies + restricted runtime app role (design D-4, tenancy-isolation spec).

Enables row-level security on every concrete workspace-scoped table and
creates the `portal_app` runtime role (`NOSUPERUSER NOBYPASSRLS`) with the
table/sequence grants it needs. All statements are written to be safely
re-runnable (idempotent): `CREATE ROLE` is guarded by an existence check,
grants are naturally idempotent, and the reverse SQL drops the policy and
disables RLS again.

Migrations run as the Postgres OWNER role (superuser locally); the owner
therefore bypasses RLS by default and this migration does not need `FORCE
ROW LEVEL SECURITY` — only non-owner, non-superuser roles (i.e. `portal_app`)
are subject to the policy below.
"""

from django.db import migrations

SCOPED_TABLES = ["workspaces_workspaceresource"]

CREATE_ROLE_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'portal_app') THEN
        CREATE ROLE portal_app WITH LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
    END IF;
END
$$;
"""

DROP_ROLE_SQL = """
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'portal_app') THEN
        DROP OWNED BY portal_app;
        DROP ROLE portal_app;
    END IF;
END
$$;
"""

GRANT_SQL = """
GRANT USAGE ON SCHEMA public TO portal_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO portal_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO portal_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO portal_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO portal_app;
"""


def _enable_rls_sql(table: str) -> str:
    return (
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;\n"
        f"CREATE POLICY ws_isolation ON {table}\n"
        "  USING (workspace_id = current_setting('app.workspace_id', true)::uuid)\n"
        "  WITH CHECK (workspace_id = current_setting('app.workspace_id', true)::uuid);\n"
    )


def _disable_rls_sql(table: str) -> str:
    return (
        f"DROP POLICY IF EXISTS ws_isolation ON {table};\n"
        f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;\n"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0002_workspace_resource"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_ROLE_SQL,
            reverse_sql=DROP_ROLE_SQL,
        ),
        migrations.RunSQL(
            sql=GRANT_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
        *[
            migrations.RunSQL(
                sql=_enable_rls_sql(table),
                reverse_sql=_disable_rls_sql(table),
            )
            for table in SCOPED_TABLES
        ],
    ]
