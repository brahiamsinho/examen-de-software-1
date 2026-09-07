import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PasswordInput } from "@/components/ui/password-input";

describe("PasswordInput", () => {
  it("masks the value by default and reveals it on toggle", () => {
    render(
      <>
        <label htmlFor="password">Contraseña</label>
        <PasswordInput id="password" />
      </>,
    );

    const input = screen.getByLabelText("Contraseña");
    expect(input).toHaveAttribute("type", "password");

    fireEvent.click(screen.getByRole("button", { name: "Mostrar contraseña" }));
    expect(input).toHaveAttribute("type", "text");

    fireEvent.click(screen.getByRole("button", { name: "Ocultar contraseña" }));
    expect(input).toHaveAttribute("type", "password");
  });
});
