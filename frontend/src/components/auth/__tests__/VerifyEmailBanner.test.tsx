import { render, screen, fireEvent } from "@testing-library/react";
import { createStore, Provider } from "jotai";
import { describe, expect, it } from "vitest";

import { VerifyEmailBanner } from "@/components/auth/VerifyEmailBanner";
import { sessionAtom } from "@/state/session";

const unverifiedUser = {
  id: "1",
  email: "a@b.com",
  full_name: "A",
  is_verified: false,
};

const verifiedUser = { ...unverifiedUser, is_verified: true };

function renderBanner(user: typeof unverifiedUser) {
  const store = createStore();
  store.set(sessionAtom, { status: "authenticated", user });
  return render(
    <Provider store={store}>
      <VerifyEmailBanner />
    </Provider>,
  );
}

describe("VerifyEmailBanner", () => {
  it("renders for an authenticated unverified user", () => {
    renderBanner(unverifiedUser);

    expect(screen.getByRole("region")).toBeInTheDocument();
  });

  it("renders null for a verified user", () => {
    const { container } = renderBanner(verifiedUser);

    expect(container).toBeEmptyDOMElement();
  });

  it("renders null when the session is not authenticated", () => {
    const store = createStore();
    store.set(sessionAtom, { status: "anonymous" });
    const { container } = render(
      <Provider store={store}>
        <VerifyEmailBanner />
      </Provider>,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("dismissing hides the banner without persisting past this render tree", () => {
    renderBanner(unverifiedUser);

    const dismissButton = screen.getByRole("button", { name: /descartar|dismiss/i });
    fireEvent.click(dismissButton);

    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });

  it("the dismiss control has an accessible name and a >=44x44 target", () => {
    renderBanner(unverifiedUser);

    const dismissButton = screen.getByRole("button", { name: /descartar|dismiss/i });
    expect(dismissButton).toHaveAccessibleName();
    expect(dismissButton.className).toMatch(/(size-11|h-11|min-h-11|w-11|min-w-11)/);
  });
});
