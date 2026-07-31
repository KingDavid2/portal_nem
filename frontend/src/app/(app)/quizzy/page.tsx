"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type MouseEvent,
} from "react";
import {
  Compass,
  FileCheck,
  ListChecks,
  Pencil,
  Plus,
  Scale,
  SendHorizontal,
  Sparkles,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { extractErrorMessage } from "@/lib/api/errors";
import {
  deleteQuizzyConversation,
  getQuizzyConversation,
  listQuizzyConversations,
  postQuizzyChat,
  renameQuizzyConversation,
  type QuizzyChatMessage,
  type QuizzyConversationSummary,
} from "@/lib/api/quizzy-chat";

/**
 * Quizzy chat surface — «1 · Vacío» / thread from `designs/quizzy.pen`,
 * plus a left history rail for persisted conversations.
 */

const STARTERS: { label: string; icon: LucideIcon }[] = [
  { label: "¿Qué PDAs cubre mi planeación de 2° A?", icon: FileCheck },
  { label: "Resume los momentos de la etapa 3", icon: ListChecks },
  { label: "¿Qué contenido oficial falta por trabajar?", icon: Compass },
  { label: "Propón un criterio de rúbrica para la etapa 2", icon: Scale },
];

function formatUpdatedAt(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("es-MX", {
    day: "numeric",
    month: "short",
  });
}

export default function QuizzyPage() {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const threadEndRef = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<QuizzyChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<
    QuizzyConversationSummary[]
  >([]);
  const [pending, setPending] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const renameInputRef = useRef<HTMLInputElement>(null);

  const refreshConversations = useCallback(async () => {
    try {
      const list = await listQuizzyConversations();
      setConversations(list);
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : extractErrorMessage(err);
      setError(detail);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  useEffect(() => {
    if (!renamingId) return;
    const input = renameInputRef.current;
    if (!input) return;
    input.focus();
    input.select();
  }, [renamingId]);

  function fillStarter(label: string) {
    setDraft(label);
    inputRef.current?.focus();
  }

  function startNewConversation() {
    setConversationId(null);
    setMessages([]);
    setError(null);
    setDraft("");
    inputRef.current?.focus();
  }

  async function openConversation(id: string) {
    if (id === conversationId || pending) return;
    setLoadingThread(true);
    setError(null);
    try {
      const detail = await getQuizzyConversation(id);
      setConversationId(detail.id);
      setMessages(
        detail.messages.map((m) => ({ role: m.role, content: m.content })),
      );
      queueMicrotask(() =>
        threadEndRef.current?.scrollIntoView({ behavior: "smooth" }),
      );
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : extractErrorMessage(err);
      setError(detail);
    } finally {
      setLoadingThread(false);
    }
  }

  async function handleDelete(id: string, event: MouseEvent<HTMLButtonElement>) {
    event.stopPropagation();
    if (pending || renamingId) return;
    try {
      await deleteQuizzyConversation(id);
      if (conversationId === id) {
        startNewConversation();
      }
      await refreshConversations();
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : extractErrorMessage(err);
      setError(detail);
    }
  }

  function beginRename(item: QuizzyConversationSummary, event: MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (pending) return;
    setRenamingId(item.id);
    setRenameDraft(item.title || "");
    setError(null);
  }

  function cancelRename() {
    setRenamingId(null);
    setRenameDraft("");
  }

  async function commitRename() {
    if (!renamingId) return;
    const next = renameDraft.trim();
    const current = conversations.find((c) => c.id === renamingId);
    if (!next || next === (current?.title ?? "")) {
      cancelRename();
      return;
    }
    try {
      const updated = await renameQuizzyConversation(renamingId, next);
      setConversations((prev) =>
        prev.map((c) => (c.id === updated.id ? { ...c, ...updated } : c)),
      );
      cancelRename();
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : extractErrorMessage(err);
      setError(detail);
    }
  }

  function handleRenameKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      cancelRename();
      return;
    }
    if (event.key === "Enter" && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void commitRename();
    }
  }

  async function sendMessage() {
    const text = draft.trim();
    if (!text || pending) return;

    setDraft("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setPending(true);

    try {
      const data = await postQuizzyChat({
        message: text,
        conversationId,
      });
      setConversationId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply },
      ]);
      await refreshConversations();
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

  const empty = messages.length === 0 && !loadingThread;

  return (
    <section className="flex h-[calc(100vh-4rem)] min-h-[32rem] overflow-hidden rounded-xl bg-card shadow-card">
      <aside className="flex w-[240px] shrink-0 flex-col border-r border-border bg-muted/30">
        <div className="border-b border-border p-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-full justify-start gap-2"
            onClick={startNewConversation}
            disabled={pending}
          >
            <Plus aria-hidden className="size-4" />
            Nueva conversación
          </Button>
        </div>
        <nav
          className="flex-1 overflow-y-auto p-2"
          aria-label="Historial de conversaciones"
        >
          {loadingList ? (
            <p className="px-2 py-3 text-xs text-muted-foreground">
              Cargando…
            </p>
          ) : conversations.length === 0 ? (
            <p className="px-2 py-3 text-xs text-muted-foreground">
              Aún no hay conversaciones
            </p>
          ) : (
            <ul className="space-y-0.5">
              {conversations.map((item) => {
                const active = item.id === conversationId;
                const renaming = renamingId === item.id;
                return (
                  <li key={item.id}>
                    <div
                      className={
                        active
                          ? "group flex items-center gap-1 rounded-md bg-primary/10 text-foreground"
                          : "group flex items-center gap-1 rounded-md text-foreground/80 hover:bg-muted/80"
                      }
                    >
                      {renaming ? (
                        <div className="min-w-0 flex-1 px-1.5 py-1">
                          <Input
                            ref={renameInputRef}
                            value={renameDraft}
                            maxLength={80}
                            aria-label="Renombrar conversación"
                            onChange={(event) =>
                              setRenameDraft(event.target.value)
                            }
                            onKeyDown={handleRenameKeyDown}
                            onBlur={() => void commitRename()}
                            className="h-8 border-border bg-background px-2 text-[13px] shadow-none"
                          />
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => void openConversation(item.id)}
                          onDoubleClick={(event) => beginRename(item, event)}
                          disabled={pending || loadingThread}
                          title="Doble clic para renombrar"
                          className="min-w-0 flex-1 px-2.5 py-2 text-left disabled:opacity-50"
                        >
                          <span className="block truncate text-[13px] font-medium">
                            {item.title || "Sin título"}
                          </span>
                          <span className="block text-[11px] text-muted-foreground">
                            {formatUpdatedAt(item.updated_at)}
                          </span>
                        </button>
                      )}
                      {!renaming ? (
                        <div className="mr-1 flex shrink-0 items-center opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                          <button
                            type="button"
                            aria-label={`Renombrar ${item.title || "conversación"}`}
                            onClick={(event) => beginRename(item, event)}
                            disabled={pending}
                            className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
                          >
                            <Pencil aria-hidden className="size-3.5" />
                          </button>
                          <button
                            type="button"
                            aria-label={`Eliminar ${item.title || "conversación"}`}
                            onClick={(event) => void handleDelete(item.id, event)}
                            disabled={pending}
                            className="rounded p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                          >
                            <Trash2 aria-hidden className="size-3.5" />
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
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

        {loadingThread ? (
          <div className="flex flex-1 items-center justify-center bg-muted/40 text-sm text-muted-foreground">
            Cargando conversación…
          </div>
        ) : empty ? (
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
                  <Icon
                    aria-hidden
                    className="size-[18px] shrink-0 text-primary"
                  />
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
              disabled={pending || loadingThread}
              className="h-10 flex-1 border-0 bg-transparent shadow-none focus-visible:border-transparent focus-visible:ring-0"
            />
            <Button
              type="submit"
              size="lg"
              disabled={pending || loadingThread || !draft.trim()}
              className="shrink-0 gap-2"
            >
              Enviar
              <SendHorizontal aria-hidden data-icon="inline-end" />
            </Button>
          </div>
        </form>
      </div>
    </section>
  );
}
