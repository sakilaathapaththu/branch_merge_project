import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Separate build folder when needed, e.g. a second instance for testing
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
