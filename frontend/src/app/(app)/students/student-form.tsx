"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Student } from "@/lib/api/students";

/** Create/edit form for Student, scoped to the currently selected Group
 * (frontend-foundation spec — "Full CRUD lifecycle for an entity"). `group`
 * is fixed by the caller, not user-editable here. */
export function StudentForm({
  groupId,
  initial,
  onSubmit,
  onCancel,
  errorMessage,
  isPending,
}: {
  groupId: number;
  initial?: Student;
  onSubmit: (input: {
    group: number;
    first_name: string;
    last_name_paternal: string;
    last_name_maternal: string;
    curp: string;
  }) => void;
  onCancel?: () => void;
  errorMessage: string | null;
  isPending: boolean;
}) {
  const [firstName, setFirstName] = useState(initial?.first_name ?? "");
  const [lastNamePaternal, setLastNamePaternal] = useState(initial?.last_name_paternal ?? "");
  const [lastNameMaternal, setLastNameMaternal] = useState(initial?.last_name_maternal ?? "");
  const [curp, setCurp] = useState(initial?.curp ?? "");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({
      group: groupId,
      first_name: firstName,
      last_name_paternal: lastNamePaternal,
      last_name_maternal: lastNameMaternal,
      curp,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold">
        {initial ? "Editar alumno" : "Nuevo alumno"}
      </h2>

      <Label className="flex flex-col items-start gap-1">
        <span>Nombre(s)</span>
        <Input
          required
          value={firstName}
          onChange={(event) => setFirstName(event.target.value)}
        />
      </Label>

      <Label className="flex flex-col items-start gap-1">
        <span>Apellido paterno</span>
        <Input
          required
          value={lastNamePaternal}
          onChange={(event) => setLastNamePaternal(event.target.value)}
        />
      </Label>

      <Label className="flex flex-col items-start gap-1">
        <span>Apellido materno (opcional)</span>
        <Input
          value={lastNameMaternal}
          onChange={(event) => setLastNameMaternal(event.target.value)}
        />
      </Label>

      <Label className="flex flex-col items-start gap-1">
        <span>CURP (opcional)</span>
        <Input
          maxLength={18}
          value={curp}
          onChange={(event) => setCurp(event.target.value.toUpperCase())}
        />
      </Label>

      {errorMessage ? (
        <p className="text-sm text-destructive" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <div className="flex gap-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? "Guardando…" : initial ? "Guardar cambios" : "Crear alumno"}
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
