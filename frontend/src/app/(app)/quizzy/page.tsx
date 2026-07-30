"use client";

import { useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import {
  Compass,
  FileCheck,
  ListChecks,
  Scale,
  SendHorizontal,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { extractErrorMessage } from "@/lib/api/errors";
import {
  postQuizzyChat,
  type QuizzyChatMessage,
} from "@/lib/api/quizzy-chat";

/**
 * Quizzy chat surface — «1 · Vacío» / thread from `designs/quizzy.pen`.
 * DEBUG stub: replies come from Cursor Composer via /api/quizzy/chat/.
 */

const STARTERS: { label: string; icon: LucideIcon }[] = [
  { label: "¿Qué PDAs cubre mi planeación de 2° A?", icon: FileCheck },
  { label: "Resume los momentos de la etapa 3", icon: ListChecks },
  { label: "¿Qué contenido oficial falta por trabajar?", icon: Compass },
  { label: "Propón un criterio de rúbrica para la etapa 2", icon: Scale },
];

export default function QuizzyPage() {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const threadEndRef = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<QuizzyChatMessage[]>([]);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function fillStarter(label: string) {
    setDraft(label);
    inputRef.current?.focus();
  }

  async function sendMessage() {
    const text = draft.trim();
    if (!text || pending) return;

    setDraft("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setPending(true);

    try {
      const data = await postQuizzyChat({ message: text, agentId });
      setAgentId(data.agent_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply },
      ]);
      queueMicrotask(() =>
        threadEndRef.current?.scrollIntoView({ behavior: "smooth" }),
      );
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : extractErrorMessage(err);
      setError(detail);
    } finally {
      setPending(false);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter" || event.nativeEvent.isComposing) return;
    event.preventDefault();
    void sendMessage();
  }

  const empty = messages.length === 0;

  return (
    <section className="flex h-[calc(100vh-4rem)] min-h-[32rem] flex-col overflow-hidden rounded-xl bg-card shadow-card">
      <header className="flex items-center gap-3 border-b border-border px-5 py-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
          <Sparkles aria-hidden className="size-5" />
        </span>
        <div className="min-w-0">
          <h1 className="text-[15px] font-semibold text-foreground">Quizzy</h1>
          <p className="truncate text-xs text-muted-foreground">
            Asistente de planeación · Cursor Composer (prueba local)
          </p>
        </div>
      </header>

      {empty ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-6 overflow-y-auto bg-muted/40 px-5 py-10">
          <div className="flex size-[98px] items-center justify-center rounded-full bg-primary/15 text-primary">
            <Sparkles aria-hidden className="size-11" />
          </div>
          <div className="max-w-lg space-y-2 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              Pregunta sobre tus planeaciones
            </h2>
            <p className="text-[13px] leading-relaxed text-muted-foreground">
              Stub de prueba: las respuestas salen de Cursor Composer. No edita
              el repo a propósito; no uses esto en producción.
            </p>
          </div>
          <div className="grid w-full max-w-3xl gap-3 sm:grid-cols-2">
            {STARTERS.map(({ label, icon: Icon }) => (
              <button
                key={label}
                type="button"
                disabled={pending}
                onClick={() => fillStarter(label)}
                className="flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3.5 text-left text-[13px] text-foreground/80 shadow-sm transition-colors hover:bg-muted/60 disabled:opacity-50"
              >
                <Icon aria-hidden className="size-[18px] shrink-0 text-primary" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto bg-muted/40 px-5 py-6">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={
                message.role === "user"
                  ? "ml-auto max-w-[min(36rem,85%)] rounded-lg bg-primary px-4 py-3 text-[13px] leading-relaxed text-primary-foreground"
                  : "mr-auto max-w-[min(40rem,90%)] rounded-lg border border-border bg-card px-4 py-3 text-[13px] leading-relaxed text-foreground shadow-sm"
              }
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
            </div>
          ))}
          {pending ? (
            <p className="mr-auto text-xs text-muted-foreground">
              Composer está pensando…
            </p>
          ) : null}
          <div ref={threadEndRef} />
        </div>
      )}

      {error ? (
        <p className="border-t border-destructive/20 bg-destructive/5 px-5 py-2 text-xs text-destructive">
          {error}
        </p>
      ) : null}

      <form
        onSubmit={handleSubmit}
        className="border-t border-border bg-card p-5"
        aria-label="Escribir mensaje a Quizzy"
      >
        <div className="flex items-center gap-2 rounded-lg border border-border bg-background px-2 py-1.5 shadow-sm focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
          <label htmlFor={inputId} className="sr-only">
            Escribe tu pregunta
          </label>
          <Input
            ref={inputRef}
            id={inputId}
            name="message"
            type="text"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe tu pregunta…"
            autoComplete="off"
            disabled={pending}
            className="h-10 flex-1 border-0 bg-transparent shadow-none focus-visible:border-transparent focus-visible:ring-0"
          />
          <Button
            type="submit"
            size="lg"
            disabled={pending || !draft.trim()}
            className="shrink-0 gap-2"
          >
            Enviar
            <SendHorizontal aria-hidden data-icon="inline-end" />
          </Button>
        </div>
      </form>
    </section>
  );
}
