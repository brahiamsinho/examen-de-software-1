import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { downloadGeneratedBackend } from "@/lib/generation_export";

describe("downloadGeneratedBackend", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    URL.createObjectURL = vi.fn(() => "blob:mock-url");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("GETs the generate endpoint of the document and triggers a download with the server filename", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response("zip", {
        status: 200,
        headers: {
          "content-type": "application/zip",
          "content-disposition": 'attachment; filename="demo-backend.zip"',
        },
      }),
    );
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    await downloadGeneratedBackend("acme", "doc-1");

    const [url] = vi.mocked(fetch).mock.calls[0]!;
    expect(String(url)).toContain("/api/orgs/acme/documents/doc-1/generate");
    expect(click).toHaveBeenCalledTimes(1);
    const anchor = click.mock.contexts[0] as HTMLAnchorElement;
    expect(anchor.download).toBe("demo-backend.zip");
    expect(anchor.href).toBe("blob:mock-url");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });

  it("falls back to a default filename when the server sends none", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("zip", { status: 200 }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    await downloadGeneratedBackend("acme", "doc-1");

    expect((click.mock.contexts[0] as HTMLAnchorElement).download).toBe("modelia-backend.zip");
  });

  it("propagates the ApiError and never triggers a download on a 422", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "sin clases", code: "nothing_to_generate" }), {
        status: 422,
        headers: { "content-type": "application/json" },
      }),
    );
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    await expect(downloadGeneratedBackend("acme", "doc-1")).rejects.toMatchObject({
      status: 422,
      detail: "sin clases",
    });
    expect(click).not.toHaveBeenCalled();
  });
});
