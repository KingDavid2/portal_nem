"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/auth-context";

/** Login screen (frontend-foundation spec — "Session/CSRF Auth Lifecycle",
 * "Full login-session-logout lifecycle"). Submits to `POST /api/auth/login/`
 * through the auth context, which the fetch layer has already wired to
 * bootstrap the CSRF cookie and echo it back as `X-CSRFToken`. */
export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsPending(true);
    try {
      await login(email, password);
      router.push("/");
      router.refresh();
    } catch {
      setError("Invalid email or password.");
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center p-8">
      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-sm flex-col gap-4"
      >
        <h1 className="text-xl font-semibold">Log in</h1>

        <label className="flex flex-col gap-1 text-sm">
          <span>Email</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-sm"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span>Password</span>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-sm"
          />
        </label>

        {error ? (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}

        <Button type="submit" disabled={isPending}>
          {isPending ? "Logging in…" : "Log in"}
        </Button>
      </form>
    </div>
  );
}
