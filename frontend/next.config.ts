import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enables a self-contained build (minimal server + only the deps it
  // needs) used by the prod stage of frontend/Dockerfile.
  output: "standalone",
};

export default nextConfig;
