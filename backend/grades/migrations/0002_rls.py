"""RLS policies for grades tables (tenancy-isolation spec — RLS Coverage Extends
to Grades Tables). Only ENABLE RLS + CREATE POLICY — no GRANT/role creation.
"""

from django.db import migrations

from workspaces.rls import disable_rls_sql, enable_rls_sql

SCOPED_TABLES = ["grades_term", "grades_activity", "grades_activityscore"]


class Migration(migrations.Migration):

    dependencies = [
        ("grades", "0001_initial"),
        ("workspaces", "0004_rls_fix_empty_setting"),
    ]

    operations = [
        migrations.RunSQL(
            sql=enable_rls_sql(table),
            reverse_sql=disable_rls_sql(table),
        )
        for table in SCOPED_TABLES
    ]
