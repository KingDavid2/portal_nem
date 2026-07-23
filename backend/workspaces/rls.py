"""Shared RLS SQL helpers (extracted from `0004_rls_fix_empty_setting`).

`0003_rls` / `0004_rls_fix_empty_setting` themselves stay frozen — their
emitted SQL is not altered by this extraction. New scoped tables (schools,
students, ...) call these helpers directly so every new RLS policy is born
in the corrected NULLIF form from the start, instead of needing its own
"fix empty setting" follow-up migration.
"""


def enable_rls_sql(table: str) -> str:
    return (
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;\n"
        f"CREATE POLICY ws_isolation ON {table}\n"
        "  USING (workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid)\n"
        "  WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true), '')::uuid);\n"
    )


def disable_rls_sql(table: str) -> str:
    return (
        f"DROP POLICY IF EXISTS ws_isolation ON {table};\n"
        f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;\n"
    )
