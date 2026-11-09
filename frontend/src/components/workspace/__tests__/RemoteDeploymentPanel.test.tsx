import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RemoteDeploymentPanel } from "@/components/workspace/RemoteDeploymentPanel";
import * as remote from "@/lib/remote_deployments";

vi.mock("@/lib/remote_deployments", async () => ({
  ...(await vi.importActual<typeof import("@/lib/remote_deployments")>("@/lib/remote_deployments")),
  getRemoteDestinations: vi.fn(), previewRemoteDeployment: vi.fn(), requestRemoteDeployment: vi.fn(),
  getRemoteConfirmation: vi.fn(), confirmRemoteDeployment: vi.fn(), getRemoteEvents: vi.fn(),
}));

const destination = { id: "dest-1", name: "VM de pruebas", destination_type: "vm_containers" as const, environment: "testing" as const, managed_config_id: "managed-test", connectivity_config_ref: "approved", capabilities: ["containers"], enabled: true };

describe("RemoteDeploymentPanel", () => {
  it("shows the no-target safety message", async () => {
    vi.mocked(remote.getRemoteDestinations).mockResolvedValueOnce([]);
    render(<RemoteDeploymentPanel orgSlug="acme" docId="doc" canDeploy />);
    expect(await screen.findByText(/No existe un destino remoto autorizado/)).toBeInTheDocument();
  });

  it("validates locally before an owner can request authorization", async () => {
    vi.mocked(remote.getRemoteDestinations).mockResolvedValueOnce([destination]);
    vi.mocked(remote.previewRemoteDeployment).mockResolvedValueOnce({ checks: [{ name: "artifact", passed: true, message: "Artefacto listo" }], warnings: ["Sin red"], can_request: true, artifact_sha256: "a", document_revision: 2 });
    render(<RemoteDeploymentPanel orgSlug="acme" docId="doc" canDeploy />);
    await screen.findByRole("option", { name: /VM de pruebas/ });
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "dest-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Validar despliegue" }));
    await screen.findByRole("button", { name: "Solicitar autorización remota" });
    expect(remote.previewRemoteDeployment).toHaveBeenCalledWith("acme", "doc", "dest-1");
    expect(screen.getByRole("button", { name: "Solicitar autorización remota" })).toBeEnabled();
  });

  it("does not expose authorization controls to a viewer", async () => {
    vi.mocked(remote.getRemoteDestinations).mockResolvedValueOnce([destination]);
    render(<RemoteDeploymentPanel orgSlug="acme" docId="doc" canDeploy={false} />);
    await waitFor(() => expect(screen.getByText(/Solo un OWNER/)).toBeInTheDocument());
    expect(screen.queryByText("Solicitar autorización remota")).not.toBeInTheDocument();
  });
});
