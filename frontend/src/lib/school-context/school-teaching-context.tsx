"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { groupsForSchoolYear, useGroupsQuery, type Group } from "@/lib/api/groups";
import { useSchoolsQuery, type School } from "@/lib/api/schools";
import {
  schoolYearsForSchool,
  useSchoolYearsQuery,
  type SchoolYear,
} from "@/lib/api/school-years";
import {
  resolveLastCycleSelection,
  resolveSchoolCascadeSelection,
  type CycleSelection,
} from "@/lib/api/school-context-selection";
import { useActiveWorkspaceId } from "@/lib/workspace/use-active-workspace";
import {
  readStoredSelection,
  sanitizeSelection,
  writeStoredSelection,
} from "@/lib/school-context/storage";

/**
 * Workspace-scoped Escuela → Ciclo → Grupo selection shared across app
 * screens (Planeaciones, Alumnos, Quizzy, …). Auto-fills último ciclo when
 * unambiguous; persists in localStorage per workspace.
 */

export type SchoolTeachingContextValue = {
  schoolId: number | null;
  schoolYearId: number | null;
  groupId: number | null;
  setSchoolId: (id: number | null) => void;
  setSchoolYearId: (id: number | null) => void;
  setGroupId: (id: number | null) => void;
  schools: School[];
  schoolYears: SchoolYear[];
  groups: Group[];
  visibleSchoolYears: SchoolYear[];
  visibleGroups: Group[];
  isReady: boolean;
};

const SchoolTeachingContext = createContext<SchoolTeachingContextValue | null>(
  null,
);

const EMPTY: CycleSelection = {
  schoolId: null,
  schoolYearId: null,
  groupId: null,
};

export function SchoolTeachingProvider({ children }: { children: ReactNode }) {
  const [workspaceId] = useActiveWorkspaceId();
  const schoolsQuery = useSchoolsQuery();
  const schoolYearsQuery = useSchoolYearsQuery();
  const groupsQuery = useGroupsQuery();

  const [selection, setSelection] = useState<CycleSelection>(EMPTY);
  const hydratedWorkspaceRef = useRef<string | null>(null);
  const autoInitDoneRef = useRef<string | null>(null);

  const schools = schoolsQuery.data ?? [];
  const schoolYears = schoolYearsQuery.data ?? [];
  const groups = groupsQuery.data ?? [];
  const listsReady =
    schoolsQuery.isSuccess && schoolYearsQuery.isSuccess && groupsQuery.isSuccess;

  // Load persisted selection when workspace changes.
  useEffect(() => {
    if (!workspaceId) {
      setSelection(EMPTY);
      hydratedWorkspaceRef.current = null;
      autoInitDoneRef.current = null;
      return;
    }
    if (hydratedWorkspaceRef.current === workspaceId) return;
    hydratedWorkspaceRef.current = workspaceId;
    autoInitDoneRef.current = null;
    setSelection(readStoredSelection(workspaceId) ?? EMPTY);
  }, [workspaceId]);

  // Sanitize against live data; auto-init último ciclo when still empty.
  useEffect(() => {
    if (!workspaceId || !listsReady) return;

    setSelection((prev) => {
      const sanitized = sanitizeSelection(prev, schools, schoolYears, groups);
      const empty =
        sanitized.schoolId === null &&
        sanitized.schoolYearId === null &&
        sanitized.groupId === null;

      if (empty && autoInitDoneRef.current !== workspaceId) {
        autoInitDoneRef.current = workspaceId;
        return resolveLastCycleSelection(schoolYears, groups);
      }

      if (
        sanitized.schoolId !== prev.schoolId ||
        sanitized.schoolYearId !== prev.schoolYearId ||
        sanitized.groupId !== prev.groupId
      ) {
        return sanitized;
      }
      return prev;
    });
  }, [workspaceId, listsReady, schools, schoolYears, groups]);

  // Persist.
  useEffect(() => {
    if (!workspaceId || hydratedWorkspaceRef.current !== workspaceId) return;
    writeStoredSelection(workspaceId, selection);
  }, [workspaceId, selection]);

  const setSchoolId = useCallback(
    (id: number | null) => {
      if (id === null) {
        setSelection(EMPTY);
        return;
      }
      const cascade = resolveSchoolCascadeSelection(id, schoolYears, groups);
      setSelection({
        schoolId: id,
        schoolYearId: cascade.schoolYearId,
        groupId: cascade.groupId,
      });
    },
    [schoolYears, groups],
  );

  const setSchoolYearId = useCallback((id: number | null) => {
    setSelection((prev) => ({
      ...prev,
      schoolYearId: id,
      groupId: null,
    }));
  }, []);

  const setGroupId = useCallback((id: number | null) => {
    setSelection((prev) => ({ ...prev, groupId: id }));
  }, []);

  const visibleSchoolYears = schoolYearsForSchool(schoolYears, selection.schoolId);
  const visibleGroups = groupsForSchoolYear(groups, selection.schoolYearId);

  const value = useMemo<SchoolTeachingContextValue>(
    () => ({
      schoolId: selection.schoolId,
      schoolYearId: selection.schoolYearId,
      groupId: selection.groupId,
      setSchoolId,
      setSchoolYearId,
      setGroupId,
      schools,
      schoolYears,
      groups,
      visibleSchoolYears,
      visibleGroups,
      isReady: listsReady,
    }),
    [
      selection,
      setSchoolId,
      setSchoolYearId,
      setGroupId,
      schools,
      schoolYears,
      groups,
      visibleSchoolYears,
      visibleGroups,
      listsReady,
    ],
  );

  return (
    <SchoolTeachingContext.Provider value={value}>
      {children}
    </SchoolTeachingContext.Provider>
  );
}

export function useSchoolTeachingContext(): SchoolTeachingContextValue {
  const ctx = useContext(SchoolTeachingContext);
  if (!ctx) {
    throw new Error(
      "useSchoolTeachingContext must be used within a SchoolTeachingProvider",
    );
  }
  return ctx;
}
