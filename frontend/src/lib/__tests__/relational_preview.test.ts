import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { downloadRelationalSql, getRelationalPreview } from "@/lib/relational_preview";

describe("relational preview client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    URL.createObjectURL = vi.fn(() => "blob:sql");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("requests the read-only relational preview endpoint", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({ tables: [], sql: "" }), { status: 200 }));

    await getRelationalPreview("acme", "doc-1");

    expect(String(vi.mocked(fetch).mock.calls[0]![0])).toContain("/api/orgs/acme/documents/doc-1/relational-preview");
  });

  it("downloads exactly the SQL displayed by the preview", () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    downloadRelationalSql('CREATE TABLE "order" ();\n', "Order diagram");

    expect(click).toHaveBeenCalledOnce();
    expect((click.mock.contexts[0] as HTMLAnchorElement).download).toBe("order-diagram-schema.sql");
  });
});
