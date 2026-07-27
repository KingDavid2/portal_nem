"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { LogoutButton } from "@/components/logout-button";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { useAuth } from "@/lib/auth/auth-context";
import { useDemoGuestRedirect } from "@/lib/demo/use-demo-guest-redirect";

export default function Home() {
  useDemoGuestRedirect();
  const { user, isLoading } = useAuth();

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold">Portal NEM</h1>

      {isLoading ? (
        <p className="text-muted-foreground">Loading session…</p>
      ) : user ? (
        <>
          <p className="text-muted-foreground">Signed in as {user.email}</p>
          <WorkspaceSwitcher enabled={Boolean(user)} />
          <Button render={<Link href="/schools" />} variant="outline">
            Ir a Escuelas
          </Button>
          <LogoutButton />
        </>
      ) : (
        <>
          <p className="text-muted-foreground">Frontend app shell is running.</p>
          <Button render={<Link href="/login" />}>Log in</Button>
        </>
      )}
    </div>
  );
}
