"""RLS policies for schools_school / schools_schoolyear / schools_group
(tenancy-isolation spec — RLS Coverage Extends to School Structure Tables).

Only ENABLE RLS + CREATE POLICY — no GRANT/role creation, since
`workspaces.0003_rls` already ran `ALTER DEFAULT PRIVILEGES` covering every
owner-created table (including these) for the `portal_app` runtime role.
"""

from django.db import migrations

from workspaces.rls import disable_rls_sql, enable_rls_sql

SCOPED_TABLES = ["schools_school", "schools_schoolyear", "schools_group"]


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0001_initial"),
        ("workspaces", "0004_rls_fix_empty_setting"),
    ]

    operations = [
        migrations.RunSQL(
            sql=enable_rls_sql(table),
            reverse_sql=disable_rls_sql(table),
        )
        for table in SCOPED_TABLES
    ]
