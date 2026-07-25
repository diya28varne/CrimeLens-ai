"use client";

import { FormEvent, useState, type CSSProperties } from "react";
import Link from "next/link";

import { chatSync, type Citation } from "@/features/ai-copilot/api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  tools?: string[];
};

const SUGGESTIONS = [
  "Give me a command brief",
  "Where are the current hotspots?",
  "Explain top station risk scores",
  "Who are the repeat offenders?",
];

export function AiCopilotPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "CrimeLens grounded copilot. I retrieve predictions, hotspots, and network facts with the same AuthZ as the rest of the API. Ask about risk, hotspots, or network — or request a brief.",
    },
  ]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    setError(null);
    setLoading(true);
    setInput("");
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    setMessages((m) => [...m, userMsg]);
    try {
      const res = await chatSync(trimmed, conversationId);
      setConversationId(res.data.conversation_id);
      setMessages((m) => [
        ...m,
        {
          id: res.data.message_id,
          role: "assistant",
          content: res.data.content,
          citations: res.data.citations,
          tools: res.data.tool_traces.map((t) => t.tool_name),
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  return (
    <div style={{ display: "grid", gap: 16, height: "calc(100vh - 3rem)", gridTemplateRows: "auto 1fr auto" }}>
      <header>
        <h1 style={{ margin: 0 }}>AI Copilot</h1>
        <p style={{ margin: "6px 0 0", color: "var(--cl-muted)", fontSize: 14 }}>
          Grounded tool answers (deterministic). Gemini streaming can replace the composer later.
        </p>
      </header>

      <div style={transcriptStyle}>
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              ...bubbleStyle,
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              background:
                m.role === "user" ? "rgba(61,139,253,0.2)" : "rgba(18, 26, 43, 0.9)",
              borderColor: m.role === "user" ? "rgba(61,139,253,0.45)" : "var(--cl-border)",
            }}
          >
            <div style={{ whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.55 }}>{m.content}</div>
            {m.tools && m.tools.length > 0 && (
              <div style={{ marginTop: 8, fontSize: 11, color: "var(--cl-muted)" }}>
                tools: {m.tools.join(", ")}
              </div>
            )}
            {m.citations && m.citations.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                {m.citations.map((c) =>
                  c.href ? (
                    <Link key={`${c.type}-${c.id}`} href={c.href} style={chipStyle}>
                      {c.type}: {c.label}
                    </Link>
                  ) : (
                    <span key={`${c.type}-${c.id}`} style={chipStyle}>
                      {c.type}: {c.label}
                    </span>
                  ),
                )}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ color: "var(--cl-muted)", fontSize: 13 }}>Retrieving grounded facts…</div>
        )}
        {error && <div style={{ color: "#ff453a", fontSize: 13 }}>{error}</div>}
      </div>

      <div style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" style={suggestionStyle} onClick={() => void send(s)}>
              {s}
            </button>
          ))}
        </div>
        <form onSubmit={onSubmit} style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8 }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about risk, hotspots, network…"
            style={inputStyle}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()} style={sendStyle}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

const transcriptStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 12,
  background: "rgba(11, 18, 32, 0.55)",
  padding: 16,
  overflowY: "auto",
  display: "flex",
  flexDirection: "column",
  gap: 12,
};

const bubbleStyle: CSSProperties = {
  maxWidth: "85%",
  border: "1px solid var(--cl-border)",
  borderRadius: 12,
  padding: "10px 12px",
};

const chipStyle: CSSProperties = {
  fontSize: 11,
  color: "var(--cl-accent)",
  border: "1px solid var(--cl-border)",
  borderRadius: 999,
  padding: "2px 8px",
  textDecoration: "none",
};

const suggestionStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  background: "rgba(18,26,43,0.8)",
  color: "var(--cl-muted)",
  borderRadius: 999,
  padding: "6px 10px",
  fontSize: 12,
  cursor: "pointer",
};

const inputStyle: CSSProperties = {
  background: "var(--cl-surface)",
  color: "var(--cl-text)",
  border: "1px solid var(--cl-border)",
  borderRadius: 10,
  padding: "12px 14px",
  fontSize: 14,
};

const sendStyle: CSSProperties = {
  background: "var(--cl-accent)",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  padding: "0 18px",
  fontWeight: 600,
  cursor: "pointer",
};
