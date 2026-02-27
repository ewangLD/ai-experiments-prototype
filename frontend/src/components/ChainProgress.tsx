import type { StepEvent } from "../api/chat";

const STEP_ORDER = ["intent", "router", "rewrite", "retrieval", "generate", "judge"];

const STEP_ICONS: Record<string, string> = {
  intent: "\u{1F3AF}",
  router: "\u{1F6A6}",
  rewrite: "\u{270F}\u{FE0F}",
  retrieval: "\u{1F50D}",
  generate: "\u{1F4AC}",
  judge: "\u{2696}\u{FE0F}",
};

interface Props {
  steps: StepEvent[];
}

export default function ChainProgress({ steps }: Props) {
  if (steps.length === 0) return null;

  // Build a map of latest state per step
  const stepMap = new Map<string, StepEvent>();
  for (const s of steps) {
    stepMap.set(s.step, s);
  }

  return (
    <div
      style={{
        margin: "8px 0 12px 0",
        padding: "10px 14px",
        backgroundColor: "#f8f9fb",
        border: "1px solid #e4e7ec",
        borderRadius: 10,
        fontSize: 13,
        lineHeight: 1.7,
      }}
    >
      {STEP_ORDER.map((key) => {
        const step = stepMap.get(key);
        if (!step) return null;

        const isRunning = step.status === "running";
        const icon = STEP_ICONS[key] || "";

        return (
          <div
            key={key}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              color: isRunning ? "#6b7280" : "#1a1a1a",
            }}
          >
            <span style={{ width: 20, textAlign: "center" }}>
              {isRunning ? (
                <span className="spinner" style={{ display: "inline-block", width: 14, height: 14, border: "2px solid #d0d0d0", borderTopColor: "#405BFF", borderRadius: "50%", animation: "spin 0.6s linear infinite" }} />
              ) : (
                icon
              )}
            </span>
            <span style={{ fontWeight: isRunning ? 400 : 500 }}>
              {step.label}
            </span>
          </div>
        );
      })}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
