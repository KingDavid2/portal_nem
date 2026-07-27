"use client";

import { useState, type FormEvent } from "react";
import { GraduationCap } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth/auth-context";
import { useDemoGuestRedirect } from "@/lib/demo/use-demo-guest-redirect";

export default function LoginPage() {
  useDemoGuestRedirect();
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(null); setIsPending(true);
    try { await login(email, password); router.push("/"); router.refresh(); }
    catch { setError("Correo o contraseña incorrectos."); }
    finally { setIsPending(false); }
  }

  return <main className="flex flex-1 flex-col items-center justify-center bg-background p-8">
    <div className="flex items-center gap-2.5"><span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground"><GraduationCap className="size-5" /></span><span className="text-xl font-semibold">portal NEM</span></div>
    <Card className="mt-6 flex w-full max-w-[460px] flex-col gap-5 p-9 shadow-card">
      <div><h1 className="text-[22px] font-semibold">Iniciar sesión</h1><p className="mt-1 text-sm text-foreground/60">Entra a tu espacio de trabajo.</p></div>
      <form onSubmit={handleSubmit} className="grid gap-4">
        <FormField label="Correo electrónico" required><Input id="email" type="email" required autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></FormField>
        <FormField label="Contraseña" required><Input id="password" type="password" required autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></FormField>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <Button type="submit" size="lg" disabled={isPending}>{isPending ? "Entrando…" : "Entrar"}</Button>
      </form>
      <p className="text-center text-sm text-foreground/60">¿No tienes cuenta? <span className="font-semibold text-primary">Crear cuenta</span></p>
    </Card>
  </main>;
}
