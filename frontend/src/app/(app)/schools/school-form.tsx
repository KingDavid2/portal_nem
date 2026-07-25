"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { FormField } from "@/components/ui/form-field";
import { Select } from "@/components/ui/select";
import type { School, SchoolInput } from "@/lib/api/schools";

const LEVEL_OPTIONS: { value: SchoolInput["level"]; label: string }[] = [
  { value: "preescolar", label: "Preescolar" },
  { value: "primaria", label: "Primaria" },
  { value: "secundaria", label: "Secundaria" },
];

/** Create/edit form for School (frontend-foundation spec — "Full CRUD
 * lifecycle for an entity"). Reused for both flows: `initial` is undefined
 * for create, populated for edit. */
export function SchoolForm({
  initial,
  onSubmit,
  onCancel,
  errorMessage,
  isPending,
}: {
  initial?: School;
  onSubmit: (input: SchoolInput) => void;
  onCancel?: () => void;
  errorMessage: string | null;
  isPending: boolean;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [cct, setCct] = useState(initial?.cct ?? "");
  const [level, setLevel] = useState<SchoolInput["level"]>(
    initial?.level ?? "preescolar",
  );

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({ name, cct, level });
  }

  return (
    <Card className="p-0"><form onSubmit={handleSubmit} className="flex flex-col gap-4 p-5">
      <h2 className="text-sm font-semibold">
        {initial ? "Editar escuela" : "Nueva escuela"}
      </h2>

      <FormField id="school-name" label="Nombre" required><Input id="school-name" required value={name} onChange={(event) => setName(event.target.value)} /></FormField>
      <FormField id="school-cct" label="CCT (opcional)"><Input id="school-cct" value={cct} onChange={(event) => setCct(event.target.value)} /></FormField>
      <FormField id="school-level" label="Nivel"><Select id="school-level" value={level} onChange={(event) => setLevel(event.target.value as SchoolInput["level"])}>{LEVEL_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</Select></FormField>

      {errorMessage ? (
        <p className="text-sm text-destructive" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <div className="flex gap-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? "Guardando…" : initial ? "Guardar cambios" : "Crear escuela"}
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
