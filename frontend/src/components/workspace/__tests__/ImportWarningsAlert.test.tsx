import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ImportWarningsAlert } from "@/components/workspace/ImportWarningsAlert";

describe("ImportWarningsAlert", () => {
  it("lists every warning and lets the user dismiss them", () => {
    const onDismiss = vi.fn();
    render(
      <ImportWarningsAlert
        warnings={["Tipo desconocido 'Geometry'", "Se ignoró Actor"]}
        onDismiss={onDismiss}
      />,
    );

    expect(screen.getByText("Tipo desconocido 'Geometry'")).toBeInTheDocument();
    expect(screen.getByText("Se ignoró Actor")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cerrar avisos" }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("renders nothing when there are no warnings", () => {
    const { container } = render(<ImportWarningsAlert warnings={[]} onDismiss={vi.fn()} />);

    expect(container).toBeEmptyDOMElement();
  });
});
