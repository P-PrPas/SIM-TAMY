import type { components } from "./api/schema";

type Speaker = components["schemas"]["Speaker"];

export type ChatMessage = {
  id: string;
  idx: number;
  speaker: Speaker;
  text: string;
  delivery: "pending" | "failed" | "sent";
};

export function appendOptimistic(messages: ChatMessage[], text: string, id: string): ChatMessage[] {
  return [...messages, { id, idx: 0, speaker: "learner", text, delivery: "pending" }];
}

export function failPending(messages: ChatMessage[], id: string): ChatMessage[] {
  return messages.map((message) => message.id === id ? { ...message, delivery: "failed" } : message);
}

export function retryPending(messages: ChatMessage[], id: string): ChatMessage[] {
  return messages.map((message) => message.id === id ? { ...message, delivery: "pending" } : message);
}

export function resolvePending(
  messages: ChatMessage[],
  id: string,
  idx: number,
  replies: Array<{ speaker: "patient" | "relative" | "system"; text: string }>,
): ChatMessage[] {
  const sent = messages.map((message) => message.id === id ? { ...message, idx, delivery: "sent" as const } : message);
  return [...sent, ...replies.map((reply, position) => ({
    id: `${id}-reply-${position}`,
    idx,
    speaker: reply.speaker,
    text: reply.text,
    delivery: "sent" as const,
  }))];
}
