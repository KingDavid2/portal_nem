"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import { useActiveWorkspaceId } from "@/lib/workspace/use-active-workspace";
import { BookOpen, GraduationCap, School, Sparkles, Users } from "lucide-react";
import { LogoutButton } from "@/components/logout-button";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { NavItem } from "@/components/ui/nav-item";
import { SchoolTeachingProvider } from "@/lib/school-context/school-teaching-context";

/**
 * Shared shell for the school-structure CRUD screens (frontend-foundation
 * spec — "CRUD Screens Cover School Structure Entities"). Gates on an
 * authenticated session AND an active workspace before rendering any screen,
 * since every entity endpoint under here is a "data request" the fetch layer
 * refuses to send without `X-Workspace-Id` (`client.ts` `MissingWorkspaceError`).
 *
 * Quizzy sits after Planeaciones per `designs/quizzy.pen` (sidebar · sparkles).
 */

const NAV_ITEMS = [
  { href: "/schools", label: "Escuelas", icon: School },
  { href: "/school-years", label: "Ciclos escolares", icon: BookOpen },
  { href: "/groups", label: "Grupos", icon: Users },
  { href: "/students", label: "Alumnos", icon: GraduationCap },
  { href: "/planeaciones", label: "Planeaciones", icon: BookOpen },
  { href: "/quizzy", label: "Quizzy", icon: Sparkles },
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
    <div className="flex min-h-full flex-1 bg-background">
      <aside className="w-[260px] shrink-0 border-r border-sidebar-border bg-sidebar p-4">
        <div className="flex h-full flex-col gap-6">
          <WorkspaceSwitcher enabled />
          <nav aria-label="Navegación principal" className="flex flex-col gap-1">
            {NAV_ITEMS.map((item) => <NavItem key={item.href} {...item} active={pathname?.startsWith(item.href) ?? false} />)}
          </nav>
          <div className="mt-auto"><LogoutButton /></div>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-8">
        <SchoolTeachingProvider>{children}</SchoolTeachingProvider>
      </main>
    </div>
  );
}
