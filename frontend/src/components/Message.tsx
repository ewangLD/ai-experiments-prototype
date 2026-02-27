import { useState } from "react";
import type { ChatResponse } from "../api/chat";
import { sendFeedback } from "../api/chat";

interface Props {
  role: "user" | "assistant";
  content: string;
  metadata?: ChatResponse;
}

export default function Message({ role, content, metadata }: Props) {
  const isUser = role === "user";
  const [feedbackGiven, setFeedbackGiven] = useState<
    "positive" | "negative" | null
  >(null);

  const handleFeedback = async (kind: "positive" | "negative") => {
    if (feedbackGiven || !metadata?.response_id) return;
    setFeedbackGiven(kind);
    await sendFeedback(metadata.response_id, kind);
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: 12,
      }}
    >
      <div style={{ maxWidth: "75%" }}>
        <div
          style={{
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
        {!isUser && metadata?.response_id && (
          <div
            style={{
              display: "flex",
              gap: 4,
              marginTop: 4,
              marginLeft: 4,
            }}
          >
            <button
              onClick={() => handleFeedback("positive")}
              disabled={feedbackGiven !== null}
              title="Helpful"
              style={{
                background: "none",
                border: "none",
                cursor: feedbackGiven ? "default" : "pointer",
                fontSize: 16,
                padding: "2px 6px",
                borderRadius: 6,
                opacity: feedbackGiven && feedbackGiven !== "positive" ? 0.3 : 1,
                backgroundColor:
                  feedbackGiven === "positive" ? "#dcfce7" : "transparent",
              }}
            >
              {"\u{1F44D}"}
            </button>
            <button
              onClick={() => handleFeedback("negative")}
              disabled={feedbackGiven !== null}
              title="Not helpful"
              style={{
                background: "none",
                border: "none",
                cursor: feedbackGiven ? "default" : "pointer",
                fontSize: 16,
                padding: "2px 6px",
                borderRadius: 6,
                opacity: feedbackGiven && feedbackGiven !== "negative" ? 0.3 : 1,
                backgroundColor:
                  feedbackGiven === "negative" ? "#fee2e2" : "transparent",
              }}
            >
              {"\u{1F44E}"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
