import { describe, expect, it } from "vitest";

import { describeEntry, type LogEntry } from "@/lib/session_log";

function change(commands: { type: string; label: string | null }[]): LogEntry {
  return {
    id: "000000000000000000000001",
    session: 1,
    kind: "change",
    author: "Ana",
    author_id: "u1",
    is_ai: false,
    summary: "",
    data: { commands, total: commands.length },
    created_at: "2026-11-07T10:00:00+00:00",
  };
}

describe("describeEntry for abstract classes", () => {
  it("says which class had its abstraction changed", () => {
    expect(describeEntry(change([{ type: "SetClassAbstract", label: "Forma" }]))).toBe(
      "Cambió la abstracción de la clase «Forma»",
    );
  });

  it("still reads well when the class cannot be named", () => {
    expect(describeEntry(change([{ type: "SetClassAbstract", label: null }]))).toBe(
      "Cambió la abstracción de una clase",
    );
  });
});
