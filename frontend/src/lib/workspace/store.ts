/**
 * Active-workspace persistence (frontend-foundation spec — "Active-Workspace
 * Context on Every Data Request"). The workspace id is a non-secret UI
 * preference, unlike a session token, so plain `localStorage` is the
 * intended storage per design.md.
 *
 * Framework-agnostic: this module has no React dependency so it can be
 * imported directly by `lib/api/client.ts` (the fetch middleware) without
 * pulling React into the fetch layer. See `useActiveWorkspaceId` in
 * `lib/workspace/use-active-workspace.ts` for the React binding.
 */

const STORAGE_KEY = "portal_nem.activeWorkspaceId";

type Listener = () => void;

const listeners = new Set<Listener>();

function readFromStorage(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

/** Returns the currently selected workspace id, or `null` if none selected
 * yet (e.g. server render, or the user hasn't picked one this session). */
export function getActiveWorkspaceId(): string | null {
  return readFromStorage();
}

/** Sets (or clears, with `null`) the active workspace and notifies
 * subscribers (e.g. the workspace switcher, and any component reading
 * `useActiveWorkspaceId`). */
export function setActiveWorkspaceId(workspaceId: string | null): void {
  if (typeof window === "undefined") return;
  if (workspaceId) {
    window.localStorage.setItem(STORAGE_KEY, workspaceId);
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
  for (const listener of listeners) listener();
}

/** Subscribes to active-workspace changes; returns an unsubscribe function.
 * Intended for `useSyncExternalStore`. */
export function subscribeActiveWorkspaceId(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
