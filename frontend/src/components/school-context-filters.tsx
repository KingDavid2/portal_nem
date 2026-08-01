import { FormField } from "@/components/ui/form-field";
import { Select } from "@/components/ui/select";

type Item = { id: number; label: string };

type Props = {
  schools: Item[];
  schoolYears: Item[];
  groups: Item[];
  schoolId: number | null;
  schoolYearId: number | null;
  groupId: number | null;
  onSchoolChange: (id: number | null) => void;
  onSchoolYearChange: (id: number | null) => void;
  onGroupChange: (id: number | null) => void;
};

/**
 * Cascading Escuela → Ciclo → Grupo selects. The parent owns school-change
 * cascade (clear or auto-fill último ciclo); this component only clears grupo
 * when ciclo changes.
 */
export function SchoolContextFilters({
  schools,
  schoolYears,
  groups,
  schoolId,
  schoolYearId,
  groupId,
  onSchoolChange,
  onSchoolYearChange,
  onGroupChange,
}: Props) {
  const number = (value: string) => (value ? Number(value) : null);

  return (
    <div className="grid gap-4 rounded-xl bg-card p-5 shadow-card md:grid-cols-3">
      <FormField label="Escuela">
        <Select
          value={schoolId ?? ""}
          onChange={(e) => onSchoolChange(number(e.target.value))}
        >
          <option value="">Selecciona una escuela…</option>
          {schools.map((x) => (
            <option key={x.id} value={x.id}>
              {x.label}
            </option>
          ))}
        </Select>
      </FormField>
      <FormField label="Ciclo escolar">
        <Select
          value={schoolYearId ?? ""}
          disabled={schoolId === null}
          onChange={(e) => {
            onSchoolYearChange(number(e.target.value));
            onGroupChange(null);
          }}
        >
          <option value="">Selecciona un ciclo escolar…</option>
          {schoolYears.map((x) => (
            <option key={x.id} value={x.id}>
              {x.label}
            </option>
          ))}
        </Select>
      </FormField>
      <FormField label="Grupo">
        <Select
          value={groupId ?? ""}
          disabled={schoolYearId === null}
          onChange={(e) => onGroupChange(number(e.target.value))}
        >
          <option value="">Selecciona un grupo…</option>
          {groups.map((x) => (
            <option key={x.id} value={x.id}>
              {x.label}
            </option>
          ))}
        </Select>
      </FormField>
    </div>
  );
}
