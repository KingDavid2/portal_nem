"use client";

import { use, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { GraduationCap } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useDemoSessionQuery } from "@/lib/api/demo";
import { meQueryKey } from "@/lib/api/hooks";
import { setActiveWorkspaceId } from "@/lib/workspace/store";
import { Button } from "@/components/ui/button";

const HEADER = (
  <div className="mb-4 flex items-center gap-2.5">
    <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
      <GraduationCap className="size-5" />
    </span>
    <span className="text-xl font-semibold">portal NEM</span>
  </div>
);

export default function DemoSessionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: session, isLoading, isError } = useDemoSessionQuery(id);

  // The poll hands back a fresh object on every tick, so the effect re-runs
  // after `ready`; entering the app is a one-shot.
  const hasEnteredRef = useRef(false);

  useEffect(() => {
    if (!session || session.status !== "ready") return;
    if (hasEnteredRef.current) return;
    hasEnteredRef.current = true;

    if (session.workspace != null) {
      setActiveWorkspaceId(session.workspace);
    }

    // Refetch and wait, rather than fire-and-forget `invalidateQueries`:
    // `useMeQuery` holds a cached `null` from when this guest was logged out,
    // and invalidation does not clear it. Navigating before the refetch lands
    // lets `useDemoGuestRedirect` on `/` read that stale `null` and bounce the
    // freshly signed-in user back to the persona picker.
    queryClient
      .refetchQueries({ queryKey: meQueryKey })
      .finally(() => router.push("/"));
  }, [session, queryClient, router]);

  if (isError) {
    return (
      <main className="flex flex-1 flex-col items-center justify-center bg-background p-8">
        {HEADER}
        <p role="alert" className="mt-4 max-w-md text-center text-sm text-destructive">
          No se pudo cargar la sesión de demostración.
        </p>
        <div className="mt-4">
          <Button render={<Link href="/demo" />} variant="outline">
            Volver a elegir perfil
          </Button>
        </div>
      </main>
    );
  }

  if (isLoading || !session || session.status === "pending") {
    return (
      <main className="flex flex-1 flex-col items-center justify-center bg-background p-8">
        {HEADER}
        <p className="mt-4 text-muted-foreground">
          Preparando tu espacio de trabajo… Esto puede tomar unos segundos.
        </p>
      </main>
    );
  }

  if (session.status === "ready") {
    return (
      <main className="flex flex-1 flex-col items-center justify-center bg-background p-8">
        {HEADER}
        <p className="mt-4 text-muted-foreground">Entrando…</p>
      </main>
    );
  }

  if (session.status === "failed") {
    const errorMessage =
      session.error_message ||
      "No se pudo preparar tu espacio de demostración. Inténtalo de nuevo.";
    return (
      <main className="flex flex-1 flex-col items-center justify-center bg-background p-8">
        {HEADER}
        <p role="alert" className="mt-4 max-w-md text-center text-sm text-destructive">
          {errorMessage}
        </p>
        <div className="mt-4">
          <Button render={<Link href="/demo" />} variant="outline">
            Volver a elegir perfil
          </Button>
        </div>
      </main>
    );
  }

  return null;
}
