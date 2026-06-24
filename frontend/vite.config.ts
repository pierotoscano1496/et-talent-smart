import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 3000,
      proxy: {
        "/auth": {
          target: env.VITE_AUTH_PROXY_URL || "http://localhost:5001",
          changeOrigin: true,
        },
        "/access": {
          target: env.VITE_ACCESS_PROXY_URL || "http://localhost:5002",
          changeOrigin: true,
        },
        "/management": {
          target: env.VITE_MANAGEMENT_PROXY_URL || "http://localhost:5003",
          changeOrigin: true,
        },
        "/reports": {
          target: env.VITE_REPORTS_PROXY_URL || "http://localhost:5004",
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: "./src/test/setup.ts",
    },
  };
});
