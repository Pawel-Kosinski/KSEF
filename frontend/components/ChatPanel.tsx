"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, MessageSquare, Pin, PinOff, Send, X } from "lucide-react";

import { HydrationSafeIcon } from "@/components/HydrationSafeIcon";
import { streamChatMessage, type ChatMessage } from "@/lib/chat";

export const CHAT_PANEL_MIN_WIDTH = 320;
export const CHAT_PANEL_MAX_WIDTH = 560;
export const CHAT_PANEL_DEFAULT_WIDTH = 400;

interface ChatPanelProps {
  open: boolean;
  pinned: boolean;
  width: number;
  onClose: () => void;
  onPinnedChange: (pinned: boolean) => void;
  onWidthChange: (width: number) => void;
}

function clampPanelWidth(value: number): number {
  return Math.min(CHAT_PANEL_MAX_WIDTH, Math.max(CHAT_PANEL_MIN_WIDTH, value));
}

const WELCOME_MESSAGE: ChatMessage = {
  role: "assistant",
  content:
    "Cześć! Jestem Twoim Wirtualnym CFO. Zapytaj o przychody, koszty lub saldo w wybranym okresie — odpytam dane z Twoich faktur KSeF.",
};

export function ChatPanel({
  open,
  pinned,
  width,
  onClose,
  onPinnedChange,
  onWidthChange,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const resizingRef = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, status, loading]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const handleResizeStart = useCallback(
    (event: React.MouseEvent) => {
      event.preventDefault();
      resizingRef.current = true;
      const startX = event.clientX;
      const startWidth = width;

      function onMouseMove(moveEvent: MouseEvent) {
        if (!resizingRef.current) return;
        const delta = startX - moveEvent.clientX;
        onWidthChange(clampPanelWidth(startWidth + delta));
      }

      function onMouseUp() {
        resizingRef.current = false;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [onWidthChange, width],
  );

  async function handleSend(event?: React.FormEvent) {
    event?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setError(null);
    setInput("");

    const historyForApi = messages.filter((message, index) => {
      if (
        index === 0 &&
        message.role === "assistant" &&
        message.content === WELCOME_MESSAGE.content
      ) {
        return false;
      }
      return message.content.trim().length > 0;
    });
    const outboundHistory: ChatMessage[] = [
      ...historyForApi,
      { role: "user", content: trimmed },
    ];

    setMessages((prev) => [...prev, { role: "user", content: trimmed }, { role: "assistant", content: "" }]);
    setLoading(true);
    setStatus(null);

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const streamEvent of streamChatMessage(outboundHistory, controller.signal)) {
        if (streamEvent.type === "text" && streamEvent.content) {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last?.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + streamEvent.content,
              };
            }
            return updated;
          });
        } else if (streamEvent.type === "tool_start" && streamEvent.tool_name) {
          setStatus(`Pobieram dane: ${streamEvent.tool_name}…`);
        } else if (streamEvent.type === "tool_result") {
          setStatus("Analizuję wyniki…");
        } else if (streamEvent.type === "error") {
          setError(streamEvent.content ?? "Wystąpił błąd podczas rozmowy z AI");
          break;
        } else if (streamEvent.type === "done") {
          setStatus(null);
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Błąd połączenia z chatem");
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.role === "assistant" && !last.content.trim()) {
          updated.pop();
        }
        return updated;
      });
    } finally {
      setLoading(false);
      setStatus(null);
    }
  }

  if (!open) return null;

  const panel = (
    <aside
      role="dialog"
      aria-modal={!pinned}
      aria-labelledby="virtual-cfo-chat-title"
      style={{ width }}
      className="relative flex h-full max-w-[92vw] flex-col border-l border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900"
    >
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Zmień szerokość panelu chatu"
        onMouseDown={handleResizeStart}
        className="absolute -left-1 top-0 z-10 h-full w-2 cursor-col-resize hover:bg-blue-500/20"
      />

      <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-4 dark:border-slate-800">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-blue-600 dark:text-blue-400">
            Virtual CFO
          </p>
          <h2
            id="virtual-cfo-chat-title"
            className="truncate text-lg font-bold text-slate-900 dark:text-white"
          >
            Chat finansowy
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Pytaj o przychody, koszty i saldo firmy
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={() => onPinnedChange(!pinned)}
            className={`rounded-lg p-2 transition-colors ${
              pinned
                ? "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
            title={pinned ? "Odepnij panel" : "Przypnij panel"}
            aria-label={pinned ? "Odepnij panel" : "Przypnij panel"}
            aria-pressed={pinned}
          >
            <HydrationSafeIcon icon={pinned ? PinOff : Pin} className="h-5 w-5" />
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Zamknij chat"
          >
            <HydrationSafeIcon icon={X} className="h-5 w-5" />
          </button>
        </div>
      </header>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[92%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                message.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100"
              }`}
            >
              {message.content ||
                (loading && index === messages.length - 1 ? (
                  <span className="inline-flex items-center gap-2 text-slate-500">
                    <HydrationSafeIcon icon={Loader2} className="h-4 w-4 animate-spin" />
                    Piszę…
                  </span>
                ) : null)}
            </div>
          </div>
        ))}

        {status ? (
          <p className="text-center text-xs text-slate-500">{status}</p>
        ) : null}

        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
            {error}
          </div>
        ) : null}
      </div>

      <form
        onSubmit={(event) => void handleSend(event)}
        className="border-t border-slate-200 p-4 dark:border-slate-800"
      >
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void handleSend();
              }
            }}
            rows={2}
            placeholder="Np. Jakie były koszty w marcu 2026?"
            disabled={loading}
            className="max-h-32 min-h-[44px] flex-1 resize-y rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-blue-500 focus:ring-2 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white transition hover:bg-blue-700 disabled:opacity-50"
            aria-label="Wyślij wiadomość"
          >
            <HydrationSafeIcon
              icon={loading ? Loader2 : Send}
              className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
          </button>
        </div>
      </form>
    </aside>
  );

  if (pinned) {
    return <div className="fixed right-0 top-0 z-40 h-full">{panel}</div>;
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/50 backdrop-blur-[1px]"
        aria-label="Zamknij chat"
        onClick={onClose}
      />
      <div className="relative h-full">{panel}</div>
    </div>
  );
}

export function ChatToggleButton({
  open,
  onClick,
}: {
  open: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition ${
        open
          ? "border-blue-600 bg-blue-50 text-blue-700 dark:border-blue-500 dark:bg-blue-950 dark:text-blue-300"
          : "border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
      }`}
    >
      <HydrationSafeIcon icon={MessageSquare} className="h-4 w-4" />
      Chat CFO
    </button>
  );
}
