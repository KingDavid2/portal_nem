"""RLS policy for students_student (tenancy-isolation spec — RLS Coverage
Extends to School Structure Tables). Only ENABLE RLS + CREATE POLICY — no
GRANT/role creation, per `workspaces.0003_rls` ALTER DEFAULT PRIVILEGES.
"""

from django.db import migrations

from workspaces.rls import disable_rls_sql, enable_rls_sql

SCOPED_TABLES = ["students_student"]


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0001_initial"),
        ("workspaces", "0004_rls_fix_empty_setting"),
    ]

    operations = [
        migrations.RunSQL(
            sql=enable_rls_sql(table),
            reverse_sql=disable_rls_sql(table),
        )
        for table in SCOPED_TABLES
    ]
