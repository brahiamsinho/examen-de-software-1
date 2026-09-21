import { fireEvent, render, screen } from "@testing-library/react";
import { createStore, Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DocumentPage from "@/app/(app)/documents/[docId]/page";
import type { UmlModel } from "@/lib/uml_documents";
import { activeOrgSlugAtom, organizationsAtom } from "@/state/organizations";

/**
 * Container (design.md DD11): unwraps `params` with `use()`, reads
 * `activeOrgSlugAtom`, wires `useDocument`, `DiagramCanvas`, the 3 add-forms,
 * `ValidationPanel`, and the click-click handler from DD8/DD9.
 * `DiagramCanvas` is mocked to a plain stub exposing one tap button per
 * class — the Cytoscape lifecycle itself is covered by
 * `DiagramCanvas.test.tsx`; this suite only proves the container's own
 * state machine and error handling.
 */
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

const useDocumentMock = vi.fn();
vi.mock("@/state/document", () => ({ useDocument: (...args: unknown[]) => useDocumentMock(...args) }));

const useDeploymentMock = vi.fn();
vi.mock("@/state/backend_deployment", () => ({
  useBackendDeployment: (...args: unknown[]) => useDeploymentMock(...args),
}));

const idleDeployment = {
  deployment: null,
  loading: false,
  busy: false,
  actionError: null,
  start: vi.fn(),
  stop: vi.fn(),
};

const downloadMock = vi.fn();
vi.mock("@/lib/generation_export", () => ({
  downloadGeneratedBackend: (...args: unknown[]) => downloadMock(...args),
}));

vi.mock("@/components/workspace/DiagramCanvas", () => ({
  DiagramCanvas: ({
    model,
    onNodeTap,
    onClaim,
  }: {
    model: UmlModel;
    onNodeTap?: (classId: string) => void;
    onClaim?: (classId: string) => void;
  }) => (
    <div>
      {model.classes.map((c) => (
        <button key={c.id} onClick={() => onNodeTap?.(c.id)}>
          Tap {c.name}
        </button>
      ))}
      {onClaim ? <button onClick={() => onClaim("c1")}>Claim c1</button> : null}
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

function renderPage(orgSlug: string | null = "acme", role: "OWNER" | "EDITOR" | "VIEWER" | null = null) {
  const store = createStore();
  store.set(activeOrgSlugAtom, orgSlug);
  if (role) {
    store.set(organizationsAtom, [{ id: "1", name: "Acme", slug: "acme", plan: "team", my_role: role }]);
  }
  return render(
    <Provider store={store}>
      <DocumentPage params={paramsPromise("doc-1")} />
    </Provider>,
  );
}

describe("DocumentPage", () => {
  beforeEach(() => {
    useDocumentMock.mockReset();
    useDeploymentMock.mockReset();
    useDeploymentMock.mockReturnValue(idleDeployment);
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

  it("renders an 'Operación' card after the 'Atributo' card under both 'Agregar' and 'Eliminar', wired to submitCommand/isSubmitting", async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    const { container } = renderPage();

    await screen.findByText("Tap Cliente");

    expect(screen.getByRole("button", { name: "Agregar operación" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Eliminar" }));
    expect(screen.getByRole("button", { name: "Eliminar operación" })).toBeInTheDocument();

    const html = container.innerHTML;
    const addAttributeIndex = html.indexOf("Agregar atributo");
    const addOperationIndex = html.indexOf("Agregar operación");
    const eliminarHeadingIndex = html.indexOf(">Eliminar</h2>");
    const removeAttributeIndex = html.indexOf('id="remove-attribute-class"');
    const removeOperationIndex = html.indexOf('id="remove-operation-class"');

    expect(addOperationIndex).toBeGreaterThan(addAttributeIndex);
    expect(removeOperationIndex).toBeGreaterThan(eliminarHeadingIndex);
    expect(removeOperationIndex).toBeGreaterThan(removeAttributeIndex);
  });

  it("renders the 3 remove controls under an 'Eliminar' heading, in class/attribute/relationship order, after the Add* block (DD7)", async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    const { container } = renderPage();

    await screen.findByText("Tap Cliente");

    expect(screen.getByRole("button", { name: "Agregar atributo" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Eliminar" }));
    expect(screen.getByRole("heading", { name: "Eliminar", level: 2 })).toBeInTheDocument();

    const removeClassButton = screen.getByRole("button", { name: "Eliminar" });
    const removeAttributeButton = screen.getByRole("button", { name: "Eliminar atributo" });
    const removeRelationshipButton = screen.getByRole("button", { name: "Eliminar relación" });

    expect(removeClassButton).toBeInTheDocument();
    expect(removeAttributeButton).toBeInTheDocument();
    expect(removeRelationshipButton).toBeInTheDocument();

    const html = container.innerHTML;
    const addBlockIndex = html.indexOf("Agregar atributo");
    const headingIndex = html.indexOf(">Eliminar</h2>");
    const classControlIndex = html.indexOf('id="remove-class-select"');
    const attributeControlIndex = html.indexOf('id="remove-attribute-class"');
    const relationshipControlIndex = html.indexOf('id="remove-relationship-select"');

    expect(addBlockIndex).toBeGreaterThan(-1);
    expect(headingIndex).toBeGreaterThan(addBlockIndex);
    expect(classControlIndex).toBeGreaterThan(headingIndex);
    expect(attributeControlIndex).toBeGreaterThan(classControlIndex);
    expect(relationshipControlIndex).toBeGreaterThan(attributeControlIndex);
  });

  it("removing the pending source class resets the click-click flow instead of showing a dead id (post-verify WARNING 2 on uml-canvas-remove-ui)", async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    const store = createStore();
    store.set(activeOrgSlugAtom, "acme");
    const { rerender } = render(
      <Provider store={store}>
        <DocumentPage params={paramsPromise("doc-1")} />
      </Provider>,
    );

    fireEvent.click(await screen.findByText("Tap Cliente"));
    expect(screen.getByText(/Selecciona la clase destino/)).toBeInTheDocument();

    // Simulate RemoveClassControl removing "Cliente" (c1) and the resulting refetch.
    const documentWithoutCliente = {
      ...document,
      model: { ...model, classes: model.classes.filter((c) => c.id !== "c1"), relationships: [] },
    };
    useDocumentMock.mockReturnValue({
      document: documentWithoutCliente,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    rerender(
      <Provider store={store}>
        <DocumentPage params={paramsPromise("doc-1")} />
      </Provider>,
    );

    expect(screen.queryByText(/Selecciona la clase destino/)).not.toBeInTheDocument();
  });

  it("a remote update that keeps the pinned class present does not disrupt the pending relationship selection (verify-report.md CRITICAL-2)", async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    const store = createStore();
    store.set(activeOrgSlugAtom, "acme");
    const { rerender } = render(
      <Provider store={store}>
        <DocumentPage params={paramsPromise("doc-1")} />
      </Provider>,
    );

    // tap A (source = Cliente) starts the click-click gesture
    fireEvent.click(await screen.findByText("Tap Cliente"));
    expect(screen.getByText(/Selecciona la clase destino/)).toBeInTheDocument();

    // Simulate a remote-origin document update arriving over the socket
    // (the same state useDocument's socket effect would produce): the
    // pinned class (Cliente/c1) is still present, only unrelated metadata
    // and revision changed.
    const documentAfterRemoteUpdate = {
      ...document,
      revision: document.revision + 1,
      metadata: { ...document.metadata, name: "Ventas (actualizado remotamente)" },
    };
    useDocumentMock.mockReturnValue({
      document: documentAfterRemoteUpdate,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    rerender(
      <Provider store={store}>
        <DocumentPage params={paramsPromise("doc-1")} />
      </Provider>,
    );

    // The pending source selection survives the remote update: the
    // "pick a target" affordance for the pinned class is still shown.
    expect(screen.getByText(/Selecciona la clase destino/)).toBeInTheDocument();

    // The gesture remains completable: tapping a target now still opens
    // the ready-to-submit relationship form.
    fireEvent.click(screen.getByText("Tap Pedido"));
    expect(screen.getByLabelText("Multiplicidad origen")).toBeInTheDocument();
    expect(screen.getByLabelText("Multiplicidad destino")).toBeInTheDocument();
  });

  it("disables all 6 command-submitting controls while isSubmitting is true (post-verify WARNING 3 on uml-canvas-remove-ui)", async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
      isSubmitting: true,
    });

    renderPage();

    await screen.findByText("Tap Cliente");

    expect(screen.getByRole("button", { name: "Agregar clase" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Agregar atributo" })).toBeDisabled();
    fireEvent.click(screen.getByRole("tab", { name: "Eliminar" }));
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Eliminar atributo" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Eliminar relación" })).toBeDisabled();
    fireEvent.click(screen.getByRole("tab", { name: "Agregar" }));

    fireEvent.click(screen.getByText("Tap Cliente"));
    fireEvent.click(screen.getByText("Tap Pedido"));
    expect(screen.getByRole("button", { name: "Confirmar relación" })).toBeDisabled();
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

/**
 * Realtime node lock affordance (design.md DD12, task 6.3): the page wires
 * `useDocument`'s `locks`/`sendClaim`/`sendPosition`/`sendRelease` into
 * `DiagramCanvas` and renders one "{owner} está moviendo {class}" line per
 * foreign-held lock (never for a lock this client itself holds).
 */
describe("DocumentPage — realtime node lock affordance (DD12)", () => {
  beforeEach(() => {
    useDocumentMock.mockReset();
  });

  it('renders "{owner} está moviendo {class}" for a foreign-held lock', async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
      locks: { c1: { ownerLabel: "Ana", mine: false } },
    });

    renderPage();

    expect(await screen.findByText(/Ana está moviendo Cliente/)).toBeInTheDocument();
  });

  it("renders no affordance when there are no foreign-held locks", async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
      locks: {},
    });

    renderPage();

    await screen.findByText("Tap Cliente");
    expect(screen.queryByText(/está moviendo/)).not.toBeInTheDocument();
  });

  it("does not render the affordance for a lock this client itself holds (mine: true)", async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
      locks: { c1: { ownerLabel: "Ana", mine: true } },
    });

    renderPage();

    await screen.findByText("Tap Cliente");
    expect(screen.queryByText(/está moviendo/)).not.toBeInTheDocument();
  });

  it("wires sendClaim from useDocument through DiagramCanvas's onClaim prop", async () => {
    const sendClaim = vi.fn();
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
      sendClaim,
    });

    renderPage();

    fireEvent.click(await screen.findByText("Claim c1"));
    expect(sendClaim).toHaveBeenCalledWith("c1");
  });
});

describe("DocumentPage — backend download", () => {
  it("downloads the generated backend of this document for the active org", async () => {
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });
    downloadMock.mockResolvedValue(undefined);

    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Descargar backend (.zip)" }));

    expect(downloadMock).toHaveBeenCalledWith("acme", "doc-1");
  });

  it("starts a backend deployment from the header 'Generar backend' button", async () => {
    const start = vi.fn();
    useDocumentMock.mockReturnValue({
      document,
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });
    useDeploymentMock.mockReturnValue({ ...idleDeployment, start });

    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Generar backend" }));

    expect(useDeploymentMock).toHaveBeenCalledWith("acme", "doc-1");
    expect(start).toHaveBeenCalledTimes(1);
  });

  describe("delete and import-into-blank actions", () => {
    const blank = { ...document, model: { ...model, classes: [], relationships: [] } };
    const stateFor = (doc: typeof document) => ({
      document: doc,
      applyDocument: vi.fn(),
      loading: false,
      error: null,
      lastValidation: null,
      submitCommand: vi.fn(),
    });

    it.each([
      ["OWNER", true],
      ["EDITOR", true],
      ["VIEWER", false],
    ] as const)("role %s: header delete button visible = %s", async (role, visible) => {
      useDocumentMock.mockReturnValue(stateFor(document));

      renderPage("acme", role);

      await screen.findByText("Tap Cliente");
      expect(screen.queryByRole("button", { name: "Eliminar diagrama" }) !== null).toBe(visible);
    });

    it("offers 'Importar XML' only on a blank diagram, and only to editors", async () => {
      useDocumentMock.mockReturnValue(stateFor(blank));
      const { unmount } = renderPage("acme", "EDITOR");
      expect(await screen.findByRole("button", { name: "Importar XML" })).toBeInTheDocument();
      unmount();

      useDocumentMock.mockReturnValue(stateFor(blank));
      const viewer = renderPage("acme", "VIEWER");
      expect(screen.queryByRole("button", { name: "Importar XML" })).not.toBeInTheDocument();
      viewer.unmount();

      useDocumentMock.mockReturnValue(stateFor(document));
      renderPage("acme", "EDITOR");
      await screen.findByText("Tap Cliente");
      expect(screen.queryByRole("button", { name: "Importar XML" })).not.toBeInTheDocument();
    });
  });
});
