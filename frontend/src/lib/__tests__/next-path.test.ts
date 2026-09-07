import { describe, expect, it } from "vitest";

import { isSafeNext, safe } from "@/lib/next-path";

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

/**
 * `isSafeNext` (design.md DD3, DV2) is the precedence-rule predicate: unlike
 * `safe()`, it distinguishes "absent/invalid" from "a real deep-link", which
 * `LoginForm` needs to let a valid `next` win over org-count branching.
 */
describe("lib/next-path isSafeNext()", () => {
  it("accepts a single-leading-slash relative path", () => {
    expect(isSafeNext("/settings")).toBe(true);
  });

  it("rejects a protocol-relative path", () => {
    expect(isSafeNext("//evil.com")).toBe(false);
  });

  it("rejects an absolute URL", () => {
    expect(isSafeNext("https://evil.com")).toBe(false);
  });

  it("rejects a javascript: URI", () => {
    expect(isSafeNext("javascript:alert(1)")).toBe(false);
  });

  it("rejects null, undefined, and empty input", () => {
    expect(isSafeNext(null)).toBe(false);
    expect(isSafeNext(undefined)).toBe(false);
    expect(isSafeNext("")).toBe(false);
  });
});
