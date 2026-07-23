"""RLS policy for lesson_plans_lessonplan (tenancy-isolation spec — RLS
coverage extends to the LessonPlan table).

Only ENABLE RLS + CREATE POLICY — no GRANT/role creation, since
`workspaces.0003_rls` already ran `ALTER DEFAULT PRIVILEGES` covering every
owner-created table (including this one) for the `portal_app` runtime role.
"""

from django.db import migrations

from workspaces.rls import disable_rls_sql, enable_rls_sql

TABLE = "lesson_plans_lessonplan"


class Migration(migrations.Migration):

    dependencies = [
        ("lesson_plans", "0001_initial"),
        ("workspaces", "0004_rls_fix_empty_setting"),
    ]

    operations = [
        migrations.RunSQL(
            sql=enable_rls_sql(TABLE),
            reverse_sql=disable_rls_sql(TABLE),
        ),
    ]
