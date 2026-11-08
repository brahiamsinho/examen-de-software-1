import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import * as saveBlob from "@/lib/save_blob";
import {
  describeEntry,
  downloadLog,
  kindLabel,
  logQuery,
  userOptions,
  type LogEntry,
  type LogSession,
} from "@/lib/session_log";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiFetchBlob: vi.fn(), apiFetch: vi.fn() };
});
vi.mock("@/lib/save_blob", () => ({ saveBlobAsFile: vi.fn() }));

function entry(overrides: Partial<LogEntry> = {}): LogEntry {
  return {
    id: 1,
    session: 1,
    kind: "change",
    author: "Ana",
    author_id: "u1",
    is_ai: false,
    summary: "",
    data: {},
    created_at: "2026-11-07T10:00:00+00:00",
    ...overrides,
  };
}

describe("logQuery", () => {
  it("is empty without filters", () => {
    expect(logQuery({})).toBe("");
  });

  it("carries the session and the user, encoded", () => {
    expect(logQuery({ session: 2, user: "ai" })).toBe("?session=2&user=ai");
    expect(logQuery({ user: "a b" })).toBe("?user=a%20b");
  });

  it("ignores an unset session (0 is a real filter only when given)", () => {
    expect(logQuery({ session: undefined, user: undefined })).toBe("");
  });
});

describe("describeEntry", () => {
  it("describes a change command by command, in Spanish, with the names involved", () => {
    const text = describeEntry(
      entry({
        data: {
          commands: [
            { type: "AddClass", label: "Pedido" },
            { type: "AddAttribute", label: "total" },
            { type: "RemoveClass", label: "Viejo" },
          ],
          total: 3,
        },
      }),
    );

    expect(text).toBe("Agregó la clase «Pedido»; Agregó el atributo «total»; Eliminó la clase «Viejo»");
  });

  it("says how many more changes there were when the entry lists fewer than it holds", () => {
    const text = describeEntry(entry({ data: { commands: [{ type: "AddClass", label: "A" }], total: 60 } }));

    expect(text).toBe("Agregó la clase «A»; y 59 cambios más");
  });

  it("falls back to the command type when it is not one it knows, and omits a missing name", () => {
    const text = describeEntry(
      entry({ data: { commands: [{ type: "SomethingNew", label: null }, { type: "RemoveClass", label: null }], total: 2 } }),
    );

    expect(text).toBe("SomethingNew; Eliminó una clase");
  });

  it("describes versions, imports and chat", () => {
    expect(describeEntry(entry({ kind: "version.restored", data: { version_number: 3 } }))).toBe("Restauró la versión 3");
    expect(describeEntry(entry({ kind: "diagram.replaced" }))).toBe("Reemplazó el contenido del diagrama con una importación");
    expect(describeEntry(entry({ kind: "chat.message", summary: "Yo hago Cliente" }))).toBe("Yo hago Cliente");
  });

  it("describes what the AI proposed and what the team decided", () => {
    expect(
      describeEntry(entry({ kind: "proposal.created", is_ai: true, data: { changes: ["a", "b"], requested_by: "Ana" } })),
    ).toBe("Propuso 2 cambios, a petición de Ana");
    expect(describeEntry(entry({ kind: "proposal.created", is_ai: true, data: { changes: ["a"] } }))).toBe("Propuso 1 cambio");
    expect(
      describeEntry(entry({ kind: "proposal.approved", data: { applied_indices: [0], total_changes: 5 } })),
    ).toBe("Aprobó la propuesta de la IA (1 de 5 cambios)");
    expect(describeEntry(entry({ kind: "proposal.rejected", data: { total_changes: 5 } }))).toBe("Rechazó la propuesta de la IA");
  });

  it("never fails on an entry whose data is missing or an unknown kind", () => {
    expect(describeEntry(entry({ kind: "change", data: {} }))).toBe("Cambió el diagrama");
    expect(describeEntry(entry({ kind: "future.kind", summary: "algo" }))).toBe("algo");
  });
});

describe("kindLabel", () => {
  it("names every kind for the badge", () => {
    expect(kindLabel("change")).toBe("Cambio");
    expect(kindLabel("chat.message")).toBe("Chat");
    expect(kindLabel("proposal.created")).toBe("Propuesta de la IA");
    expect(kindLabel("proposal.approved")).toBe("Aprobada");
    expect(kindLabel("proposal.rejected")).toBe("Rechazada");
    expect(kindLabel("version.restored")).toBe("Versión");
    expect(kindLabel("diagram.replaced")).toBe("Importación");
    expect(kindLabel("future.kind")).toBe("future.kind");
  });
});

describe("userOptions", () => {
  const session = (n: number, actors: LogSession["actors"]): LogSession => ({
    session: n,
    started_at: "2026-11-07T10:00:00+00:00",
    ended_at: "2026-11-07T10:30:00+00:00",
    entries: 1,
    actors,
  });

  it("lists each person once, plus the AI when it took part", () => {
    const options = userOptions([
      session(1, [{ id: "u1", label: "Ana", is_ai: false }, { id: null, label: "IA", is_ai: true }]),
      session(2, [{ id: "u1", label: "Ana", is_ai: false }, { id: "u2", label: "Luis", is_ai: false }]),
    ]);

    expect(options).toEqual([
      { value: "u1", label: "Ana" },
      { value: "ai", label: "IA" },
      { value: "u2", label: "Luis" },
    ]);
  });

  it("leaves out an author that cannot be filtered on (an account that was deleted)", () => {
    expect(userOptions([session(1, [{ id: null, label: "Bruno", is_ai: false }])])).toEqual([]);
  });
});

describe("downloadLog", () => {
  beforeEach(() => {
    vi.mocked(api.apiFetchBlob).mockReset();
    vi.mocked(saveBlob.saveBlobAsFile).mockReset();
  });

  it("downloads the CSV with the current filters and hands it to the browser", async () => {
    const blob = new Blob(["x"]);
    vi.mocked(api.apiFetchBlob).mockResolvedValue({ blob, filename: "session-log-d1.csv" });

    await downloadLog("acme", "d1", { session: 2, user: "ai" });

    expect(api.apiFetchBlob).toHaveBeenCalledWith("/api/orgs/acme/documents/d1/log/export?session=2&user=ai");
    expect(saveBlob.saveBlobAsFile).toHaveBeenCalledWith(blob, "session-log-d1.csv");
  });

  it("uses a fallback file name when the server sends none", async () => {
    const blob = new Blob(["x"]);
    vi.mocked(api.apiFetchBlob).mockResolvedValue({ blob, filename: null });

    await downloadLog("acme", "d1", {});

    expect(saveBlob.saveBlobAsFile).toHaveBeenCalledWith(blob, "bitacora.csv");
  });
});
