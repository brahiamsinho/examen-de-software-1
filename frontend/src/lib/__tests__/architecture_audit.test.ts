import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { downloadArchitectureAudit, getArchitectureAudit, type ArchitectureAuditReport } from "@/lib/architecture_audit";

const report: ArchitectureAuditReport = {
  contract_version: "1.0", rules_version: "1.0", document: { id: "doc-1", revision: 2 },
  summary: { ERROR: 0, WARNING: 1, INFO: 0 },
  findings: [{ id: "ar-002-test", rule_id: "AR-002", rule_name: "Acoplamiento elevado", rule_purpose: "Detecta relaciones", severity: "WARNING", title: "Acoplamiento", explanation: "Explicación", evidence: "Evidencia", element_ids: ["class-1"], recommendation: "Revisar" }],
};

describe("architecture audit client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    URL.createObjectURL = vi.fn(() => "blob:audit");
    URL.revokeObjectURL = vi.fn();
  });
  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("requests the read-only audit endpoint", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(report), { status: 200 }));
    await getArchitectureAudit("acme", "doc-1");
    expect(String(vi.mocked(fetch).mock.calls[0]![0])).toContain("/api/orgs/acme/documents/doc-1/architecture-audit");
  });

  it("downloads the displayed report as JSON or Markdown", () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    downloadArchitectureAudit(report, "Audit Demo", "json");
    downloadArchitectureAudit(report, "Audit Demo", "markdown");
    expect(click).toHaveBeenCalledTimes(2);
    expect((click.mock.contexts[0] as HTMLAnchorElement).download).toBe("audit-demo-architecture-audit.json");
    expect((click.mock.contexts[1] as HTMLAnchorElement).download).toBe("audit-demo-architecture-audit.md");
  });
});
