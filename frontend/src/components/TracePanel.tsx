import type { ChatResponse } from "../api/chat";

interface Props {
  metadata: ChatResponse | null;
}

export default function TracePanel({ metadata }: Props) {
  if (!metadata) return null;

  const { intent, entities, quality } = metadata;

  return (
    <details
      style={{
        margin: "8px 0",
        padding: "8px 12px",
        backgroundColor: "#fafafa",
        border: "1px solid #e0e0e0",
        borderRadius: 8,
        fontSize: 13,
      }}
    >
      <summary style={{ cursor: "pointer", fontWeight: 600, color: "#555" }}>
        Trace Details
      </summary>
      <div style={{ marginTop: 8 }}>
        <div>
          <strong>Intent:</strong> {intent}
        </div>
        {entities.length > 0 && (
          <div>
            <strong>Entities:</strong> {entities.join(", ")}
          </div>
        )}
        <div style={{ marginTop: 4 }}>
          <strong>Quality:</strong>{" "}
          <span style={{ color: quality.passed ? "#16a34a" : "#dc2626" }}>
            {quality.passed ? "PASS" : "FAIL"}
          </span>{" "}
          — relevance: {quality.relevance.toFixed(2)}, faithfulness:{" "}
          {quality.faithfulness.toFixed(2)}
        </div>
      </div>
    </details>
  );
}
