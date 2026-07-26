"use client";

import { FormEvent, useEffect, useState, type CSSProperties } from "react";
import Link from "next/link";
import { useTranslation } from "react-i18next";

import { chatSync, type Citation } from "@/features/ai-copilot/api";
import { useAppLocale } from "@/shared/i18n/useAppLocale";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  tools?: string[];
};

const SUGGESTION_KEYS = ["brief", "hotspots", "riskScores", "repeatOffenders"] as const;

export function AiCopilotPanel() {
  const { t } = useTranslation("ai");
  const locale = useAppLocale();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMessages((prev) => {
      const welcome: ChatMessage = {
        id: "welcome",
        role: "assistant",
        content: t("copilot.welcome"),
      };
      if (prev.length === 0 || (prev.length === 1 && prev[0]?.id === "welcome")) {
        return [welcome];
      }
      if (prev[0]?.id === "welcome") {
        return [welcome, ...prev.slice(1)];
      }
      return prev;
    });
  }, [locale, t]);

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
          tools: res.data.tool_traces.map((tr) => tr.tool_name),
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("copilot.errorChat"));
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
        <h1 style={{ margin: 0 }}>{t("copilot.title")}</h1>
        <p style={{ margin: "6px 0 0", color: "var(--cl-muted)", fontSize: 14 }}>{t("copilot.subtitle")}</p>
      </header>

      <div style={transcriptStyle}>
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              ...bubbleStyle,
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              background: m.role === "user" ? "rgba(61,139,253,0.2)" : "rgba(18, 26, 43, 0.9)",
              borderColor: m.role === "user" ? "rgba(61,139,253,0.45)" : "var(--cl-border)",
            }}
          >
            <div style={{ whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.55 }}>{m.content}</div>
            {m.tools && m.tools.length > 0 && (
              <div style={{ marginTop: 8, fontSize: 11, color: "var(--cl-muted)" }}>
                {t("copilot.tools", { list: m.tools.join(", ") })}
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
        {loading && <div style={{ color: "var(--cl-muted)", fontSize: 13 }}>{t("copilot.retrieving")}</div>}
        {error && <div style={{ color: "#ff453a", fontSize: 13 }}>{error}</div>}
      </div>

      <div style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {SUGGESTION_KEYS.map((key) => {
            const text = t(`copilot.suggestions.${key}`);
            return (
              <button key={key} type="button" style={suggestionStyle} onClick={() => void send(text)}>
                {text}
              </button>
            );
          })}
        </div>
        <form onSubmit={onSubmit} style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8 }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t("copilot.placeholder")}
            style={inputStyle}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()} style={sendStyle}>
            {t("copilot.send")}
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
