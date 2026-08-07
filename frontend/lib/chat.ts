import { parseApiErrorMessage } from "@/lib/apiErrors";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export type ChatStreamEventType = "text" | "tool_start" | "tool_result" | "done" | "error";

export interface ChatStreamEvent {
  type: ChatStreamEventType;
  content?: string;
  tool_name?: string;
  tool_call_id?: string;
}

export async function* streamChatMessage(
  messages: ChatMessage[],
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch("/api/v1/chat/message", {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    },
    credentials: "include",
    cache: "no-store",
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(
      parseApiErrorMessage(payload, response.status, "Nie udało się wysłać wiadomości"),
    );
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Serwer nie zwrócił strumienia odpowiedzi");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part
        .split("\n")
        .find((entry) => entry.startsWith("data: "));
      if (!line) continue;
      try {
        yield JSON.parse(line.slice(6)) as ChatStreamEvent;
      } catch {
        // pomijamy uszkodzone ramki SSE
      }
    }
  }
}
