import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Input } from "@/components/ui/input";

describe("Input", () => {
  it("renders as a labeled text field", () => {
    render(
      <>
        <label htmlFor="email">Correo electrónico</label>
        <Input id="email" type="email" />
      </>,
    );

    expect(screen.getByLabelText("Correo electrónico")).toBeInTheDocument();
  });

  it("applies aria-invalid styling hooks when marked invalid", () => {
    render(<Input aria-invalid placeholder="value" />);

    expect(screen.getByPlaceholderText("value")).toHaveAttribute("aria-invalid", "true");
  });
});
