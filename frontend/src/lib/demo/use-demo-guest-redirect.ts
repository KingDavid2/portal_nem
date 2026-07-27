"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import { useDemoModeQuery } from "@/lib/api/demo";

/**
 * Client-side analogue of the Rails DemoModeAuthentication concern.
 *
 * When demo mode is enabled and the caller is a logged-out guest, redirects
 * them to the persona picker at `/demo` instead of showing the normal login
 * page. Applied only at `/` and `/login` on purpose — deeper routes that
 * require auth should fall back to the standard auth flow.
 *
 * Never redirects while either the demo-mode query or the auth query is
 * still loading, to avoid bouncing a signed-in user due to a race.
 */
export function useDemoGuestRedirect(): void {
  const { data: demoMode, isLoading: demoLoading } = useDemoModeQuery();
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (demoLoading || authLoading) return;
    if (demoMode !== true) return;
    if (user !== null) return;
    router.replace("/demo");
  }, [demoMode, demoLoading, authLoading, user, router]);
}
