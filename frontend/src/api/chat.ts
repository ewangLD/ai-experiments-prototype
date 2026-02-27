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
  intent: string;
  entities: string[];
  quality: QualityMetadata;
  sources: { title: string; url: string }[];
}

const API_BASE = "/chat";

export async function sendMessage(
  message: string,
  sessionId: string,
  conversationHistory: ChatMessage[]
): Promise<ChatResponse> {
  const res = await fetch(API_BASE, {
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

  return res.json();
}
