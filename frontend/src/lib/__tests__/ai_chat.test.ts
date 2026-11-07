import { describe, expect, it } from "vitest";

import { mentionsAi, upsertChatMessage, type ChatMessage } from "@/lib/ai_chat";

function message(id: number, overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id,
    document_id: "d1",
    author: "Ana",
    author_id: "u1",
    is_ai: false,
    content: `m${id}`,
    created_at: "2026-11-07T10:00:00Z",
    ...overrides,
  };
}

describe("upsertChatMessage", () => {
  it("appends a new message", () => {
    expect(upsertChatMessage([message(1)], message(2)).map((m) => m.id)).toEqual([1, 2]);
  });

  it("is idempotent: the same message arriving over HTTP and the socket appears once", () => {
    const once = upsertChatMessage([message(1)], message(2));

    expect(upsertChatMessage(once, message(2)).map((m) => m.id)).toEqual([1, 2]);
  });

  it("keeps messages ordered by id even when they arrive out of order", () => {
    const list = upsertChatMessage(upsertChatMessage([], message(3)), message(2));

    expect(list.map((m) => m.id)).toEqual([2, 3]);
  });

  it("does not mutate the list it receives", () => {
    const original = [message(1)];

    upsertChatMessage(original, message(2));

    expect(original).toHaveLength(1);
  });

  it("keeps only the latest messages so a long chat cannot grow without bound", () => {
    let list: ChatMessage[] = [];
    for (let id = 1; id <= 250; id += 1) list = upsertChatMessage(list, message(id));

    expect(list).toHaveLength(200);
    expect(list[0]!.id).toBe(51);
    expect(list[199]!.id).toBe(250);
  });
});

describe("mentionsAi", () => {
  it.each(["@IA qué falta", "hola @ia, ayuda", "Ayuda @IA"])("detects %s", (text) => {
    expect(mentionsAi(text)).toBe(true);
  });

  it.each(["escríbeme a hola@ia.com", "@IAmigos qué tal", "la IA sola"])("ignores %s", (text) => {
    expect(mentionsAi(text)).toBe(false);
  });
});
