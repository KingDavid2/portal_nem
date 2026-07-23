"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold">
        {initial ? "Editar ciclo escolar" : "Nuevo ciclo escolar"}
      </h2>

      <Label className="flex flex-col items-start gap-1">
        <span>Etiqueta (p. ej. 2024-2025)</span>
        <Input
          required
          maxLength={9}
          value={label}
          onChange={(event) => setLabel(event.target.value)}
        />
      </Label>

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
    </form>
  );
}
