import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GenerationProfilePanel } from "@/components/workspace/GenerationProfilePanel";
import { ApiError } from "@/lib/api";
import type { UmlClass } from "@/lib/uml_documents";

const classes: UmlClass[] = [
  {
    id: "class-order",
    name: "Order",
    visibility: "public",
    attributes: [
      { id: "attr-total", name: "total", type: "Decimal", visibility: "private" },
      { id: "attr-code", name: "code", type: "String", visibility: "private" },
    ],
    operations: [],
  },
  {
    id: "class-customer",
    name: "Customer",
    visibility: "public",
    attributes: [{ id: "attr-email", name: "email", type: "String", visibility: "private" }],
    operations: [],
  },
];

function renderPanel(options: {
  generationMetadata?: Record<string, unknown>;
  onSubmit?: ReturnType<typeof vi.fn>;
  modelClasses?: UmlClass[];
} = {}) {
  const onSubmit = options.onSubmit ?? vi.fn().mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
  render(
    <GenerationProfilePanel
      classes={options.modelClasses ?? classes}
      generationMetadata={options.generationMetadata ?? {}}
      onSubmit={onSubmit as unknown as React.ComponentProps<typeof GenerationProfilePanel>["onSubmit"]}
    />,
  );
  return { onSubmit };
}

const selectTarget = (name: string) => {
  fireEvent.change(screen.getByLabelText("Elemento"), { target: { value: name } });
};

const setControl = (name: string, value: "unset" | "true" | "false") => {
  fireEvent.change(screen.getByLabelText(name), { target: { value } });
};

describe("GenerationProfilePanel", () => {
  it("renders class and attribute target options from classes", () => {
    renderPanel();

    expect(screen.getByRole("option", { name: "Clase: Order" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Atributo: Order.total" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Clase: Customer" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Atributo: Customer.email" })).toBeInTheDocument();
  });

  it("shows an empty disabled state when there are no targets", () => {
    renderPanel({ modelClasses: [] });

    expect(screen.getByText("No hay clases ni atributos disponibles para perfilar.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar perfil" })).toBeDisabled();
  });

  it("selecting a class shows only class-level controls", () => {
    renderPanel();

    selectTarget("class-order");

    expect(screen.getByLabelText("Auditable")).toBeInTheDocument();
    expect(screen.getByLabelText("Solo lectura")).toBeInTheDocument();
    expect(screen.getByLabelText("CRUD")).toBeInTheDocument();
    expect(screen.queryByLabelText("Buscable")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Ordenable")).not.toBeInTheDocument();
  });

  it("selecting an attribute shows only attribute-level controls", () => {
    renderPanel();

    selectTarget("attr-total");

    expect(screen.getByLabelText("Buscable")).toBeInTheDocument();
    expect(screen.getByLabelText("Ordenable")).toBeInTheDocument();
    expect(screen.getByLabelText("Solo lectura")).toBeInTheDocument();
    expect(screen.queryByLabelText("Auditable")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("CRUD")).not.toBeInTheDocument();
  });

  it("replaces visible controls when switching between target kinds", () => {
    renderPanel({
      generationMetadata: {
        "class-order": { profile: { auditable: true } },
        "attr-total": { profile: { searchable: false } },
      },
    });

    selectTarget("class-order");
    expect(screen.getByLabelText("Auditable")).toHaveValue("true");

    selectTarget("attr-total");
    expect(screen.getByLabelText("Buscable")).toHaveValue("false");
    expect(screen.queryByLabelText("Auditable")).not.toBeInTheDocument();
  });

  it("prefills class profile booleans and full CRUD arrays", () => {
    renderPanel({
      generationMetadata: {
        "class-order": {
          profile: { auditable: true, readOnly: false, crud: ["create", "read", "update", "delete"] },
        },
      },
    });

    selectTarget("class-order");

    expect(screen.getByLabelText("Auditable")).toHaveValue("true");
    expect(screen.getByLabelText("Solo lectura")).toHaveValue("false");
    expect(screen.getByLabelText("CRUD")).toHaveValue("true");
  });

  it("prefills attribute profile booleans", () => {
    renderPanel({
      generationMetadata: {
        "attr-total": { profile: { searchable: true, sortable: false, readOnly: true } },
      },
    });

    selectTarget("attr-total");

    expect(screen.getByLabelText("Buscable")).toHaveValue("true");
    expect(screen.getByLabelText("Ordenable")).toHaveValue("false");
    expect(screen.getByLabelText("Solo lectura")).toHaveValue("true");
  });

  it("treats malformed metadata as all controls unset without crashing", () => {
    renderPanel({
      generationMetadata: {
        "class-order": { profile: ["bad"] },
        "attr-total": null,
        "attr-code": { profile: { searchable: "yes", sortable: null, readOnly: 1 } },
        "class-customer": { profile: { crud: ["create", "read"] } },
      },
    });

    selectTarget("class-order");
    expect(screen.getByLabelText("Auditable")).toHaveValue("unset");
    expect(screen.getByLabelText("Solo lectura")).toHaveValue("unset");
    expect(screen.getByLabelText("CRUD")).toHaveValue("unset");

    selectTarget("attr-code");
    expect(screen.getByLabelText("Buscable")).toHaveValue("unset");
    expect(screen.getByLabelText("Ordenable")).toHaveValue("unset");
    expect(screen.getByLabelText("Solo lectura")).toHaveValue("unset");

    selectTarget("class-customer");
    expect(screen.getByLabelText("CRUD")).toHaveValue("unset");
  });

  it("submits declared class controls only and maps crud=false to an empty array", async () => {
    const { onSubmit } = renderPanel();

    selectTarget("class-order");
    setControl("Auditable", "true");
    setControl("CRUD", "false");
    fireEvent.click(screen.getByRole("button", { name: "Guardar perfil" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
    expect(onSubmit).toHaveBeenCalledWith({
      type: "SetGenerationProfile",
      element_id: "class-order",
      profile: { auditable: true, crud: [] },
    });
  });

  it("submits declared attribute controls only", async () => {
    const { onSubmit } = renderPanel();

    selectTarget("attr-total");
    setControl("Buscable", "true");
    setControl("Solo lectura", "false");
    fireEvent.click(screen.getByRole("button", { name: "Guardar perfil" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
    expect(onSubmit).toHaveBeenCalledWith({
      type: "SetGenerationProfile",
      element_id: "attr-total",
      profile: { searchable: true, readOnly: false },
    });
  });

  it("submits profile null when all visible controls are unset", async () => {
    const { onSubmit } = renderPanel();

    selectTarget("attr-total");
    fireEvent.click(screen.getByRole("button", { name: "Guardar perfil" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
    expect(onSubmit).toHaveBeenCalledWith({
      type: "SetGenerationProfile",
      element_id: "attr-total",
      profile: null,
    });
  });

  it("maps crud=true to all operations and never sends a raw boolean", async () => {
    const { onSubmit } = renderPanel();

    selectTarget("class-order");
    setControl("CRUD", "true");
    fireEvent.click(screen.getByRole("button", { name: "Guardar perfil" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
    const command = onSubmit.mock.calls[0][0];
    expect(command.profile).toEqual({ crud: ["create", "read", "update", "delete"] });
    expect(typeof command.profile.crud).not.toBe("boolean");
  });

  it("successful submit keeps the target selected and normalizes visible controls", async () => {
    renderPanel();

    selectTarget("class-order");
    setControl("Auditable", "true");
    setControl("Solo lectura", "false");
    fireEvent.click(screen.getByRole("button", { name: "Guardar perfil" }));

    await waitFor(() => expect(screen.getByLabelText("Elemento")).toHaveValue("class-order"));
    expect(screen.getByLabelText("Auditable")).toHaveValue("true");
    expect(screen.getByLabelText("Solo lectura")).toHaveValue("false");
    expect(screen.getByLabelText("CRUD")).toHaveValue("unset");
  });

  it("displays ApiError details and keeps the form mounted", async () => {
    const onSubmit = vi.fn().mockRejectedValue(
      new ApiError({ status: 422, code: "invalid_command_payload", detail: "Perfil inválido" }),
    );
    renderPanel({ onSubmit });

    selectTarget("attr-total");
    setControl("Buscable", "true");
    fireEvent.click(screen.getByRole("button", { name: "Guardar perfil" }));

    expect(await screen.findByText("Perfil inválido")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar perfil" })).toBeInTheDocument();
    expect(screen.getByLabelText("Buscable")).toHaveValue("true");
  });

  it("displays a generic message for unexpected errors", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("boom"));
    renderPanel({ onSubmit });

    selectTarget("attr-total");
    fireEvent.click(screen.getByRole("button", { name: "Guardar perfil" }));

    expect(await screen.findByText("Ocurrió un error inesperado. Intenta de nuevo.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar perfil" })).toBeInTheDocument();
  });
});
