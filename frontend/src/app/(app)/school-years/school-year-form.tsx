"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { FormField } from "@/components/ui/form-field";
import type { SchoolYear } from "@/lib/api/school-years";

/** Create/edit form for SchoolYear, scoped to the currently selected School
 * (frontend-foundation spec — "Full CRUD lifecycle for an entity"). `school`
 * is fixed by the caller, not user-editable here. */
export function SchoolYearForm({
  schoolId,
  initial,
  onSubmit,
  onCancel,
  errorMessage,
  isPending,
}: {
  schoolId: number;
  initial?: SchoolYear;
  onSubmit: (input: { school: number; label: string }) => void;
  onCancel?: () => void;
  errorMessage: string | null;
  isPending: boolean;
}) {
  const [label, setLabel] = useState(initial?.label ?? "");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ school: schoolId, label });
  }

  return (
    <Card className="p-0"><form onSubmit={handleSubmit} className="flex flex-col gap-4 p-5">
      <h2 className="text-sm font-semibold">
        {initial ? "Editar ciclo escolar" : "Nuevo ciclo escolar"}
      </h2>

      <FormField id="school-year-label" label="Etiqueta (p. ej. 2024-2025)" required><Input id="school-year-label" required maxLength={9} value={label} onChange={(event) => setLabel(event.target.value)} /></FormField>

      {errorMessage ? (
        <p className="text-sm text-destructive" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <div className="flex gap-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? "Guardando…" : initial ? "Guardar cambios" : "Crear ciclo escolar"}
        </Button>
        {onCancel ? (
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancelar
          </Button>
        ) : null}
      </div>
    </form></Card>
  );
}
