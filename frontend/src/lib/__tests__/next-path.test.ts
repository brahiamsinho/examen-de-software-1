import { describe, expect, it } from "vitest";

import { safe } from "@/lib/next-path";

/**
 * Open-redirect guard for the post-login `next` query param (design.md
 * DD5). Tested as a pure function, apart from any component, per design's
 * routing-contract testing strategy.
 */
describe("lib/next-path safe()", () => {
  it("accepts a single-leading-slash relative path", () => {
    expect(safe("/dashboard/settings")).toBe("/dashboard/settings");
  });

  it("falls back to /dashboard for a protocol-relative path", () => {
    expect(safe("//evil.com")).toBe("/dashboard");
  });

  it("falls back to /dashboard for an absolute URL", () => {
    expect(safe("https://evil.com")).toBe("/dashboard");
  });

  it("falls back to /dashboard for null, undefined, or empty input", () => {
    expect(safe(null)).toBe("/dashboard");
    expect(safe(undefined)).toBe("/dashboard");
    expect(safe("")).toBe("/dashboard");
  });
});
