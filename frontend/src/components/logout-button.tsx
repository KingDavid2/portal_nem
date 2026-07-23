"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/auth-context";

export function LogoutButton() {
  const { logout } = useAuth();
  const router = useRouter();
  const [isPending, setIsPending] = useState(false);

  return (
    <Button
      variant="outline"
      disabled={isPending}
      onClick={async () => {
        setIsPending(true);
        try {
          await logout();
          router.refresh();
        } finally {
          setIsPending(false);
        }
      }}
    >
      {isPending ? "Logging out…" : "Log out"}
    </Button>
  );
}
