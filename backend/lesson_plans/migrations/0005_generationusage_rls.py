"""RLS policy for lesson_plans_generationusage (tenancy-isolation spec — RLS
coverage extends to every scoped table).

Mirrors `0002_rls` exactly, using the same `workspaces.rls` helpers: a scoped
table without RLS is a tenancy hole, since the runtime `portal_app` role would
otherwise be able to read and increment another workspace's quota ledger.

Only ENABLE RLS + CREATE POLICY — no GRANT/role creation, since
`workspaces.0003_rls` already ran `ALTER DEFAULT PRIVILEGES` covering every
owner-created table (including this one) for the `portal_app` runtime role.
"""

from django.db import migrations

from workspaces.rls import disable_rls_sql, enable_rls_sql

TABLE = "lesson_plans_generationusage"


class Migration(migrations.Migration):

    dependencies = [
        ("lesson_plans", "0004_generationusage"),
    ]

    operations = [
        migrations.RunSQL(
            sql=enable_rls_sql(TABLE),
            reverse_sql=disable_rls_sql(TABLE),
        ),
    ]
