import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// `lib/env.ts` throws at import time when NEXT_PUBLIC_API_URL is unset
// (frontend-auth-integration Phase 1). Vitest does not run Next.js's own
// `.env`/`.env.local` loader, so tests need a value here regardless of the
// local dev environment.
process.env.NEXT_PUBLIC_API_URL ??= "http://localhost:8000";

afterEach(() => {
  cleanup();
});
