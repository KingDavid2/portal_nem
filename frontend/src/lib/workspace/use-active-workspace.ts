"use client";

import { useCallback, useSyncExternalStore } from "react";
import {
  getActiveWorkspaceId,
  setActiveWorkspaceId,
  subscribeActiveWorkspaceId,
} from "@/lib/workspace/store";

function getServerSnapshot(): string | null {
  return null;
}

/** React binding over the active-workspace store: re-renders whenever the
 * active workspace changes (e.g. via the workspace switcher). */
export function useActiveWorkspaceId(): [string | null, (id: string | null) => void] {
  const workspaceId = useSyncExternalStore(
    subscribeActiveWorkspaceId,
    getActiveWorkspaceId,
    getServerSnapshot,
  );

  const setWorkspaceId = useCallback((id: string | null) => {
    setActiveWorkspaceId(id);
  }, []);

  return [workspaceId, setWorkspaceId];
}
