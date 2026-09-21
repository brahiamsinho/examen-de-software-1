import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enables a self-contained build (minimal server + only the deps it
  // needs) used by the prod stage of frontend/Dockerfile.
  output: "standalone",
  // Dev-only: the Next dev badge defaults to bottom-left, where it covered
  // the sidebar's logout control. Has no effect on production builds.
  devIndicators: { position: "bottom-right" },
};

export default nextConfig;
