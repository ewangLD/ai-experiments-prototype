export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface QualityMetadata {
  relevance: number;
  faithfulness: number;
  passed: boolean;
}

export interface ChatResponse {
  reply: string;
  response_id: string;
  intent: string;
  entities: string[];
  quality: QualityMetadata;
  sources: { title: string; url: string }[];
}

export async function sendFeedback(
  responseId: string,
  kind: "positive" | "negative"
): Promise<void> {
  await fetch("/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ response_id: responseId, kind }),
  });
}

export interface StepEvent {
  step: string;
  status: "running" | "done";
  label: string;
  detail?: Record<string, unknown>;
}

export async function sendMessageStream(
  message: string,
  sessionId: string,
  conversationHistory: ChatMessage[],
  onStep: (step: StepEvent) => void
): Promise<ChatResponse> {
  const res = await fetch("/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      conversation_history: conversationHistory,
    }),
  });

  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: ChatResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const parts = buffer.split("\n\n");
    buffer = parts.pop()!; // keep incomplete chunk

    for (const part of parts) {
      const lines = part.split("\n");
      let eventType = "";
      let data = "";

      for (const line of lines) {
        if (line.startsWith("event: ")) eventType = line.slice(7);
        else if (line.startsWith("data: ")) data = line.slice(6);
      }

      if (!eventType || !data) continue;

      if (eventType === "step") {
        onStep(JSON.parse(data) as StepEvent);
      } else if (eventType === "result") {
        result = JSON.parse(data) as ChatResponse;
      }
    }
  }

  if (!result) {
    throw new Error("No result received from stream");
  }

  return result;
}
