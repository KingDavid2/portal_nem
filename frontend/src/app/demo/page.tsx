"use client";

import { GraduationCap } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  useCreateDemoSessionMutation,
  useDemoPersonasQuery,
  type PersonaEnum,
} from "@/lib/api/demo";

const DEMO_PASSWORD = "DemoPlan2026!";

export default function DemoPage() {
  const router = useRouter();
  const { data: personas, isLoading, isError } = useDemoPersonasQuery();
  const mutation = useCreateDemoSessionMutation();

  function selectPersona(personaKey: string) {
    mutation.mutate(personaKey as PersonaEnum, {
      onSuccess: (session) => {
        router.push(`/demo/${session.id}`);
      },
    });
  }

  if (isLoading) {
    return (
      <main className="flex flex-1 flex-col items-center justify-center bg-background p-8">
        <div className="mb-4 flex items-center gap-2.5">
          <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <GraduationCap className="size-5" />
          </span>
          <span className="text-xl font-semibold">portal NEM</span>
        </div>
        <p className="text-muted-foreground">Cargando perfiles de demostración…</p>
      </main>
    );
  }

  if (isError || !personas) {
    return (
      <main className="flex flex-1 flex-col items-center justify-center bg-background p-8">
        <div className="mb-4 flex items-center gap-2.5">
          <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <GraduationCap className="size-5" />
          </span>
          <span className="text-xl font-semibold">portal NEM</span>
        </div>
        <p role="alert" className="text-sm text-destructive">
          No se pudieron cargar los perfiles. Inténtalo de nuevo.
        </p>
      </main>
    );
  }

  return (
    <main className="flex flex-1 flex-col items-center bg-background p-8">
      <div className="mb-6 flex items-center gap-2.5">
        <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <GraduationCap className="size-5" />
        </span>
        <span className="text-xl font-semibold">portal NEM</span>
      </div>

      <h1 className="mb-2 text-2xl font-semibold">Modo Demo</h1>
      <p className="mb-8 max-w-xl text-center text-muted-foreground">
        Elige un perfil de demostración para explorar el portal. Cada perfil
        configura un espacio de trabajo con datos de ejemplo.
      </p>

      <div className="grid w-full max-w-4xl grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {personas.map((persona) => (
          <Card
            key={persona.key}
            className="flex flex-col gap-3 p-6"
          >
            <h2 className="text-lg font-semibold">{persona.label}</h2>
            <p className="text-sm text-muted-foreground">{persona.description}</p>
            {persona.features.length > 0 && (
              <ul className="list-inside list-disc text-sm">
                {persona.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
            )}
            <div className="mt-auto pt-2">
              <Button
                className="w-full"
                onClick={() => selectPersona(persona.key)}
                disabled={mutation.isPending}
              >
                {mutation.isPending ? "Creando sesión…" : "Probar"}
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <footer className="mt-12 text-center text-sm text-muted-foreground">
        <p>Contraseña de demostración:</p>
        <code className="rounded-md bg-muted px-2 py-0.5 font-mono text-foreground">
          {DEMO_PASSWORD}
        </code>
      </footer>
    </main>
  );
}