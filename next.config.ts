import type { NextConfig } from "next";

// Backend FastAPI (RNF-03): el frontend solo consume la API REST /api/v1
const DSS_API_URL = process.env.DSS_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  output: "standalone",
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${DSS_API_URL}/api/v1/:path*` }];
  },
};

export default nextConfig;
