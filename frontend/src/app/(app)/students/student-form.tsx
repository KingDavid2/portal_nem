"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { FormField } from "@/components/ui/form-field";
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
    <Card className="p-0"><form onSubmit={handleSubmit} className="flex flex-col gap-4 p-5">
      <h2 className="text-sm font-semibold">
        {initial ? "Editar alumno" : "Nuevo alumno"}
      </h2>

      <FormField id="student-first-name" label="Nombre(s)" required><Input id="student-first-name" required value={firstName} onChange={(event) => setFirstName(event.target.value)} /></FormField>
      <FormField id="student-last-name" label="Apellido paterno" required><Input id="student-last-name" required value={lastNamePaternal} onChange={(event) => setLastNamePaternal(event.target.value)} /></FormField>
      <FormField id="student-maternal-name" label="Apellido materno (opcional)"><Input id="student-maternal-name" value={lastNameMaternal} onChange={(event) => setLastNameMaternal(event.target.value)} /></FormField>
      <FormField id="student-curp" label="CURP (opcional)"><Input id="student-curp" maxLength={18} value={curp} onChange={(event) => setCurp(event.target.value.toUpperCase())} /></FormField>

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
    </form></Card>
  );
}
