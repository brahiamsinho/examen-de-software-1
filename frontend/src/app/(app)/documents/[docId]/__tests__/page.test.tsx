import { fireEvent, render, screen } from "@testing-library/react";
import { createStore, Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DocumentPage from "@/app/(app)/documents/[docId]/page";
import type { UmlModel } from "@/lib/uml_documents";
import { activeOrgSlugAtom } from "@/state/organizations";

/**
 * Container (design.md DD11): unwraps `params` with `use()`, reads
 * `activeOrgSlugAtom`, wires `useDocument`, `DiagramCanvas`, the 3 add-forms,
 * `ValidationPanel`, and the click-click handler from DD8/DD9.
 * `DiagramCanvas` is mocked to a plain stub exposing one tap button per
 * class — the Cytoscape lifecycle itself is covered by
 * `DiagramCanvas.test.tsx`; this suite only proves the container's own
 * state machine and error handling.
 */
const useDocumentMock = vi.fn();
vi.mock("@/state/document", () => ({ useDocument: (...args: unknown[]) => useDocumentMock(...args) }));

vi.mock("@/components/workspace/DiagramCanvas", () => ({
  DiagramCanvas: ({
    model,
    onNodeTap,
  }: {
    model: UmlModel;
    onNodeTap?: (classId: string) => void;
  }) => (
    <div>
      {model.classes.map((c) => (
        <button key={c.id} onClick={() => onNodeTap?.(c.id)}>
          Tap {c.name}
        </button>
      ))}
    </div>
  ),
}));

/**
 * React's `use()` recognizes an already-settled "thenable" via its
 * `status`/`value` fields and unwraps it synchronously without suspending —
 * the same fast path Next.js's own `params` promise relies on. A plain
 * `Promise.resolve(...)` only settles on a later microtask, so it would
 * force this container through an actual Suspense cycle for no reason in
 * a unit test.
 */
function paramsPromise(docId: string) {
  const resolved = { docId };
  return Object.assign(Promise.resolve(resolved), { status: "fulfilled", value: resolved });
}

const model: UmlModel = {
  classes: [
    { id: "c1", name: "Cliente", visibility: "public", attributes: [], operations: [] },
    { id: "c2", name: "Pedido", visibility: "public", attributes: [], operations: [] },
  ],
  enumerations: [],
  relationships: [
    {
      id: "r1",
      kind: "association",
      source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
      target: { class_id: "c2", multiplicity: { lower: 0, upper: null }, role: null },
      name: null,
    },
  ],
  generation_metadata: {},
};

const document = {
  id: "doc-1",
  owner_id: "1",
  revision: 1,
  metadata: { name: "Ventas", description: "" },
  model,
  layout: { positions: {} },
  created_at: "2026-09-12T10:00:00Z",
  updated_at: "2026-09-12T10:00:00Z",
};

function renderPage(orgSlug: string | null = "acme") {
  const store = createStore();
  store.set(activeOrgSlugAtom, orgSlug);
  return render(
    <Provider store={store}>
      <DocumentPage params={paramsPromise("doc-1")} />
    </Provider>,
  );
}

describe("DocumentPage", () => {
  beforeEach(() => {
    useDocumentMock.mockReset();
  });

  it("renders classes and relationships count from document.model", async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    renderPage();

    expect(await screen.findByText("Tap Cliente")).toBeInTheDocument();
    expect(screen.getByText("Clases: 2")).toBeInTheDocument();
    expect(screen.getByText("Relaciones: 1")).toBeInTheDocument();
  });

  it("renders a not-found state on a notFound error instead of a crash", async () => {
    useDocumentMock.mockReturnValue({
      document: null,
      loading: false,
      error: { message: "Not found", notFound: true },
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    renderPage();

    expect(await screen.findByText(/no encontrado/i)).toBeInTheDocument();
  });

  it("renders a distinct generic error state for a non-404 failure", async () => {
    useDocumentMock.mockReturnValue({
      document: null,
      loading: false,
      error: { message: "Server error", notFound: false },
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    renderPage();

    expect(await screen.findByText(/ocurrió un error/i)).toBeInTheDocument();
    expect(screen.queryByText(/no encontrado/i)).not.toBeInTheDocument();
  });

  it("click-click: tap class A sets pending source, tap A again cancels, tap A then tap B opens AddRelationshipControl", async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    renderPage();

    const tapCliente = await screen.findByText("Tap Cliente");
    fireEvent.click(tapCliente);
    expect(screen.getByText(/Selecciona la clase destino/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Multiplicidad origen")).not.toBeInTheDocument();

    fireEvent.click(tapCliente);
    expect(screen.queryByText(/Selecciona la clase destino/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Multiplicidad origen")).not.toBeInTheDocument();

    fireEvent.click(tapCliente);
    fireEvent.click(screen.getByText("Tap Pedido"));

    expect(screen.getByLabelText("Multiplicidad origen")).toBeInTheDocument();
    expect(screen.getByLabelText("Multiplicidad destino")).toBeInTheDocument();
  });

  it("cancelling a chosen source also clears the stale target, so a fresh source needs a new target tap", async () => {
    const documentWithThreeClasses = {
      ...document,
      model: {
        ...model,
        classes: [
          ...model.classes,
          { id: "c3", name: "Factura", visibility: "public" as const, attributes: [], operations: [] },
        ],
      },
    };
    useDocumentMock.mockReturnValue({
      document: documentWithThreeClasses,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    renderPage();

    // tap A (source = Cliente)
    fireEvent.click(await screen.findByText("Tap Cliente"));
    // tap B (target = Pedido) -> ready-to-submit form for A -> B
    fireEvent.click(screen.getByText("Tap Pedido"));
    expect(screen.getByLabelText("Multiplicidad origen")).toBeInTheDocument();

    // tap A again -> cancel gesture: must clear BOTH source and target
    fireEvent.click(screen.getByText("Tap Cliente"));
    expect(screen.queryByLabelText("Multiplicidad origen")).not.toBeInTheDocument();
    expect(screen.queryByText(/Selecciona la clase destino/)).not.toBeInTheDocument();

    // tap C (a third, different class) -> must NOT immediately show a
    // ready-to-submit "C to B" pairing from the stale target
    fireEvent.click(screen.getByText("Tap Factura"));
    expect(screen.queryByLabelText("Multiplicidad origen")).not.toBeInTheDocument();
    expect(screen.getByText(/Selecciona la clase destino/)).toBeInTheDocument();
  });

  it("shows a durable note when a relationship references a nonexistent class", async () => {
    const documentWithDangling = {
      ...document,
      model: {
        ...model,
        relationships: [
          ...model.relationships,
          {
            id: "r2",
            kind: "association" as const,
            source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
            target: { class_id: "missing", multiplicity: { lower: 1, upper: 1 }, role: null },
            name: null,
          },
        ],
      },
    };
    useDocumentMock.mockReturnValue({
      document: documentWithDangling,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    renderPage();

    expect(
      await screen.findByText(/no se muestran por referirse a una clase inexistente/i),
    ).toBeInTheDocument();
  });

  it("does not show the dangling-relationship note when all endpoints resolve", async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    renderPage();

    await screen.findByText("Tap Cliente");
    expect(
      screen.queryByText(/no se muestran por referirse a una clase inexistente/i),
    ).not.toBeInTheDocument();
  });
});
