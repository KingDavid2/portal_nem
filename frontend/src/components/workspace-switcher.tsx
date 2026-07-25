"use client";

import { useEffect } from "react";
import { useWorkspacesQuery } from "@/lib/api/hooks";
import { useActiveWorkspaceId } from "@/lib/workspace/use-active-workspace";
import { Select } from "@/components/ui/select";

/**
 * Active-workspace switcher (frontend-foundation spec — "Active-Workspace
 * Context on Every Data Request"). Lists the caller's memberships from
 * `GET /api/workspaces/` and lets them pick which one is active; the
 * selection is what the fetch layer's `X-CSRFToken`/`X-Workspace-Id`
 * middleware reads for every subsequent data request.
 */
export function WorkspaceSwitcher({ enabled }: { enabled: boolean }) {
  const { data: memberships, isLoading } = useWorkspacesQuery(enabled);
  const [activeWorkspaceId, setActiveWorkspaceId] = useActiveWorkspaceId();

  // Default to the first membership once memberships load and nothing is
  // selected yet, so data requests aren't blocked immediately after login.
  useEffect(() => {
    if (!activeWorkspaceId && memberships && memberships.length > 0) {
      setActiveWorkspaceId(memberships[0].id);
    }
  }, [activeWorkspaceId, memberships, setActiveWorkspaceId]);

  if (!enabled) return null;
  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading workspaces…</p>;
  }
  if (!memberships || memberships.length === 0) {
    return <p className="text-sm text-muted-foreground">No workspaces available.</p>;
  }

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">Workspace</span>
      <Select
        className="h-auto w-auto border-border bg-background px-2 py-1"
        value={activeWorkspaceId ?? ""}
        onChange={(event) => setActiveWorkspaceId(event.target.value || null)}
      >
        {memberships.map((membership) => (
          <option key={membership.id} value={membership.id}>
            {membership.name} ({membership.role})
          </option>
        ))}
      </Select>
    </label>
  );
}
