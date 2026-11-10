import { describe, expect, it } from "vitest";

import { mentionsAi, upsertChatMessage, type ChatMessage } from "@/lib/ai_chat";

// ObjectIds are 24 hex characters; this builds a sortable one from a small number.
const oid = (n: number) => n.toString(16).padStart(24, "0");

function message(n: number, overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: oid(n),
    document_id: "d1",
    author: "Ana",
    author_id: "u1",
    is_ai: false,
    content: `m${n}`,
    created_at: "2026-11-07T10:00:00Z",
    ...overrides,
  };
}

describe("upsertChatMessage", () => {
  it("appends a new message", () => {
    expect(upsertChatMessage([message(1)], message(2)).map((m) => m.id)).toEqual([oid(1), oid(2)]);
  });

  it("is idempotent: the same message arriving over HTTP and the socket appears once", () => {
    const once = upsertChatMessage([message(1)], message(2));

    expect(upsertChatMessage(once, message(2)).map((m) => m.id)).toEqual([oid(1), oid(2)]);
  });

  it("keeps messages ordered by id even when they arrive out of order", () => {
    const list = upsertChatMessage(upsertChatMessage([], message(3)), message(2));

    expect(list.map((m) => m.id)).toEqual([oid(2), oid(3)]);
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
    expect(list[0]!.id).toBe(oid(51));
    expect(list[199]!.id).toBe(oid(250));
  });
});

describe("mentionsAi", () => {
  it.each(["@IA qué falta", "hola @ia, ayuda", "Ayuda @IA"])("detects %s", (text) => {
    expect(mentionsAi(text)).toBe(true);
  });

  // Accented letters count as word characters, exactly like the backend's Unicode `\w`.
  it.each(["@IAñ qué tal", "ñ@IA", "@IA1", "hey_@IA"])("ignores %s like the backend does", (text) => {
    expect(mentionsAi(text)).toBe(false);
  });

  it.each(["escríbeme a hola@ia.com", "@IAmigos qué tal", "la IA sola"])("ignores %s", (text) => {
    expect(mentionsAi(text)).toBe(false);
  });
});
