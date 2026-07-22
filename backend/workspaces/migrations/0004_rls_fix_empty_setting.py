"""Fix RLS predicate to tolerate current_setting() returning "" (D9 gap).

Discovered by the D9 cross-tenant leak test: once a `SET LOCAL
app.workspace_id` value's transaction ends, `current_setting('app.workspace_id',
true)` does not return NULL — it returns an empty string `''`. The original
policy predicate (`current_setting(...)::uuid`) then raised
`InvalidTextRepresentation` on `''::uuid` instead of denying the row, which
is a functional bug (an error, not fail-closed denial) for any query issued
on a connection with no active workspace context. `NULLIF(..., '')` maps the
empty string to NULL before the cast, so an absent/cleared setting correctly
evaluates the predicate to NULL/false (deny), never an error.
"""

from django.db import migrations

SCOPED_TABLES = ["workspaces_workspaceresource"]


def _fixed_policy_sql(table: str) -> str:
    return (
        f"DROP POLICY IF EXISTS ws_isolation ON {table};\n"
        f"CREATE POLICY ws_isolation ON {table}\n"
        "  USING (workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid)\n"
        "  WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid);\n"
    )


def _original_policy_sql(table: str) -> str:
    return (
        f"DROP POLICY IF EXISTS ws_isolation ON {table};\n"
        f"CREATE POLICY ws_isolation ON {table}\n"
        "  USING (workspace_id = current_setting('app.workspace_id', true)::uuid)\n"
        "  WITH CHECK (workspace_id = current_setting('app.workspace_id', true)::uuid);\n"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0003_rls"),
    ]

    operations = [
        migrations.RunSQL(
            sql=_fixed_policy_sql(table),
            reverse_sql=_original_policy_sql(table),
        )
        for table in SCOPED_TABLES
    ]
