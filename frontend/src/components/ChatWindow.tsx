import { useState, useRef, useEffect } from "react";
import type { ChatMessage, ChatResponse, StepEvent } from "../api/chat";
import { sendMessageStream } from "../api/chat";
import Message from "./Message";
import TracePanel from "./TracePanel";
import ChainProgress from "./ChainProgress";

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  metadata?: ChatResponse;
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState<StepEvent[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sessionId = useRef(
    `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, steps]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setSteps([]);

    try {
      const history: ChatMessage[] = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await sendMessageStream(
        text,
        sessionId.current,
        history,
        (step) => setSteps((prev) => [...prev, step])
      );

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.reply, metadata: response },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : "Something went wrong"}`,
        },
      ]);
    } finally {
      setLoading(false);
      setSteps([]);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        maxWidth: 720,
        margin: "0 auto",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid #e0e0e0",
          fontWeight: 700,
          fontSize: 18,
          color: "#1a1a1a",
        }}
      >
        LaunchDarkly Support Chat
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
        {messages.length === 0 && (
          <div
            style={{
              textAlign: "center",
              color: "#999",
              marginTop: 80,
              fontSize: 14,
            }}
          >
            Ask a question about LaunchDarkly to get started.
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i}>
            <Message
              role={msg.role}
              content={msg.content}
              metadata={msg.metadata}
            />
            {msg.metadata && <TracePanel metadata={msg.metadata} />}
          </div>
        ))}
        {loading && <ChainProgress steps={steps} />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div
        style={{
          display: "flex",
          gap: 8,
          padding: "12px 20px",
          borderTop: "1px solid #e0e0e0",
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about LaunchDarkly..."
          disabled={loading}
          style={{
            flex: 1,
            padding: "10px 14px",
            borderRadius: 8,
            border: "1px solid #d0d0d0",
            fontSize: 14,
            outline: "none",
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            padding: "10px 20px",
            borderRadius: 8,
            border: "none",
            backgroundColor: "#405BFF",
            color: "#fff",
            fontSize: 14,
            fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading || !input.trim() ? 0.5 : 1,
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
