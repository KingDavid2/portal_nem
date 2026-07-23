"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold">
        {initial ? "Editar escuela" : "Nueva escuela"}
      </h2>

      <Label className="flex flex-col items-start gap-1">
        <span>Nombre</span>
        <Input
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </Label>

      <Label className="flex flex-col items-start gap-1">
        <span>CCT (opcional)</span>
        <Input value={cct} onChange={(event) => setCct(event.target.value)} />
      </Label>

      <Label className="flex flex-col items-start gap-1">
        <span>Nivel</span>
        <select
          value={level}
          onChange={(event) => setLevel(event.target.value as SchoolInput["level"])}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm"
        >
          {LEVEL_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </Label>

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
    </form>
  );
}
