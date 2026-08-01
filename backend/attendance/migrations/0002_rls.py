"""RLS policy for attendance_attendancerecord (tenancy-isolation spec — RLS
Coverage Extends to Attendance Records). Only ENABLE RLS + CREATE POLICY — no
GRANT/role creation, per `workspaces.0003_rls` ALTER DEFAULT PRIVILEGES.
"""

from django.db import migrations

from workspaces.rls import disable_rls_sql, enable_rls_sql

SCOPED_TABLES = ["attendance_attendancerecord"]


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0001_initial"),
        ("workspaces", "0004_rls_fix_empty_setting"),
    ]

    operations = [
        migrations.RunSQL(
            sql=enable_rls_sql(table),
            reverse_sql=disable_rls_sql(table),
        )
        for table in SCOPED_TABLES
    ]
