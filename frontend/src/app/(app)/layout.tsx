"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import { useActiveWorkspaceId } from "@/lib/workspace/use-active-workspace";
import { cn } from "@/lib/utils";

/**
 * Shared shell for the school-structure CRUD screens (frontend-foundation
 * spec — "CRUD Screens Cover School Structure Entities"). Gates on an
 * authenticated session AND an active workspace before rendering any screen,
 * since every entity endpoint under here is a "data request" the fetch layer
 * refuses to send without `X-Workspace-Id` (`client.ts` `MissingWorkspaceError`).
 */

const NAV_ITEMS = [
  { href: "/schools", label: "Escuelas" },
  { href: "/school-years", label: "Ciclos escolares" },
  { href: "/groups", label: "Grupos" },
  { href: "/students", label: "Alumnos" },
  { href: "/planeaciones", label: "Planeaciones" },
] as const;

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const [activeWorkspaceId] = useActiveWorkspaceId();
  const pathname = usePathname();

  if (isLoading) {
    return <p className="p-8 text-muted-foreground">Cargando sesión…</p>;
  }

  if (!user) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8">
        <p className="text-muted-foreground">Debes iniciar sesión primero.</p>
        <Link href="/login" className="text-primary underline underline-offset-4">
          Ir a iniciar sesión
        </Link>
      </div>
    );
  }

  if (!activeWorkspaceId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8">
        <p className="text-muted-foreground">
          Selecciona un workspace en la página principal primero.
        </p>
        <Link href="/" className="text-primary underline underline-offset-4">
          Ir a inicio
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 p-8">
      <nav className="flex flex-wrap gap-4 border-b border-border pb-4">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "text-sm font-medium text-muted-foreground hover:text-foreground",
              pathname?.startsWith(item.href) && "text-foreground underline underline-offset-4",
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      {children}
    </div>
  );
}
