import type { ChatResponse } from "../api/chat";

interface Props {
  role: "user" | "assistant";
  content: string;
  metadata?: ChatResponse;
}

export default function Message({ role, content, metadata }: Props) {
  const isUser = role === "user";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: 12,
      }}
    >
      <div
        style={{
          maxWidth: "75%",
          padding: "10px 14px",
          borderRadius: 12,
          backgroundColor: isUser ? "#405BFF" : "#f0f0f0",
          color: isUser ? "#fff" : "#1a1a1a",
          fontSize: 14,
          lineHeight: 1.5,
          whiteSpace: "pre-wrap",
        }}
      >
        {content}
        {metadata?.sources && metadata.sources.length > 0 && (
          <div
            style={{
              marginTop: 8,
              paddingTop: 8,
              borderTop: "1px solid rgba(0,0,0,0.1)",
              fontSize: 12,
            }}
          >
            <strong>Sources:</strong>
            {metadata.sources.map((s, i) => (
              <div key={i}>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: isUser ? "#c8d0ff" : "#405BFF" }}
                >
                  {s.title || s.url}
                </a>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
