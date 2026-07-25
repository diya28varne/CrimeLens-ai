import { apiFetch } from "@/shared/api/client";

export type Citation = {
  type: string;
  id: string;
  label: string;
  href?: string | null;
};

export type ChatSyncResult = {
  conversation_id: string;
  message_id: string;
  content: string;
  citations: Citation[];
  tool_traces: Array<{ tool_name: string; status: string; latency_ms?: number | null }>;
};

export async function chatSync(message: string, conversationId?: string | null) {
  return apiFetch<{ data: ChatSyncResult }>("/ai/chat/sync", {
    method: "POST",
    body: JSON.stringify({
      message,
      conversation_id: conversationId || undefined,
      mode: "ask",
    }),
  });
}

export async function listConversations() {
  return apiFetch<{
    data: Array<{ id: string; title: string; updated_at: string }>;
  }>("/ai/conversations");
}
