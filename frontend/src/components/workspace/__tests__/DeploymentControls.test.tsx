import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DeploymentActions, DeploymentNotices, DeploymentUrl } from "@/components/workspace/DeploymentControls";
import type { Deployment } from "@/lib/backend_deployments";

function deployment(overrides: Partial<Deployment>): Deployment {
  return {
    id: "d1",
    document_id: "doc-1",
    status: "running",
    error: "",
    log_tail: "",
    public_path: "/api/run/d1/",
    public_url: "http://localhost:8000/api/run/d1/",
    openapi_url: "http://localhost:8000/api/run/d1/v3/api-docs",
    docs_url: "http://localhost:8000/api/run/d1/swagger-ui/index.html",
    created_at: "2026-09-20T10:00:00Z",
    updated_at: "2026-09-20T10:00:00Z",
    ...overrides,
  };
}

const handlers = { busy: false, actionError: null, onStart: vi.fn(), onStop: vi.fn() };

describe("DeploymentActions", () => {
  it("idle: offers 'Generar backend' and starts on click", () => {
    const onStart = vi.fn();
    render(<DeploymentActions deployment={null} {...handlers} onStart={onStart} />);

    fireEvent.click(screen.getByRole("button", { name: "Generar backend" }));

    expect(onStart).toHaveBeenCalledTimes(1);
  });

  it("in progress: shows the current step and disables the button", () => {
    render(<DeploymentActions deployment={deployment({ status: "building" })} {...handlers} />);

    expect(screen.getByRole("button", { name: "Construyendo…" })).toBeDisabled();
  });

  it("running: shows the badge, the API docs link (new tab), Detener and Regenerar", () => {
    const onStop = vi.fn();
    render(<DeploymentActions deployment={deployment({})} {...handlers} onStop={onStop} />);

    expect(screen.getByText("En ejecución")).toBeInTheDocument();
    const docs = screen.getByRole("link", { name: "Documentación API" });
    expect(docs).toHaveAttribute("href", "http://localhost:8000/api/run/d1/swagger-ui/index.html");
    expect(docs).toHaveAttribute("target", "_blank");
    expect(screen.queryByRole("link", { name: "Abrir API" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Regenerar" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Detener" }));
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it("failed: offers 'Reintentar'", () => {
    render(<DeploymentActions deployment={deployment({ status: "failed" })} {...handlers} />);

    expect(screen.getByRole("button", { name: "Reintentar" })).toBeEnabled();
  });
});

describe("DeploymentNotices", () => {
  it("failed: shows the reason and the build log", () => {
    render(
      <DeploymentNotices
        deployment={deployment({ status: "failed", error: "mvn exited 1", log_tail: "[ERROR] boom" })}
        actionError={null}
      />,
    );

    expect(screen.getByText("mvn exited 1")).toBeInTheDocument();
    expect(screen.getByText("Registro de construcción")).toBeInTheDocument();
    expect(screen.getByText("[ERROR] boom")).toBeInTheDocument();
  });

  it("shows a friendly action error and nothing else when running without log", () => {
    const { container, rerender } = render(
      <DeploymentNotices deployment={deployment({})} actionError="Alcanzaste el límite" />,
    );
    expect(screen.getByText("Alcanzaste el límite")).toBeInTheDocument();
    expect(screen.queryByText("Registro de construcción")).not.toBeInTheDocument();

    rerender(<DeploymentNotices deployment={deployment({})} actionError={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("DeploymentUrl", () => {
  it("shows the backend URL linking to the docs only while running", () => {
    const { rerender } = render(<DeploymentUrl deployment={deployment({})} />);

    expect(screen.getByRole("link", { name: "http://localhost:8000/api/run/d1/" })).toHaveAttribute(
      "href",
      "http://localhost:8000/api/run/d1/swagger-ui/index.html",
    );

    rerender(<DeploymentUrl deployment={deployment({ status: "stopped" })} />);
    expect(screen.queryByText("URL del backend:")).toBeNull();
  });
});
