import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite dev server configuration.
// The React dev server runs on :5173, the FastAPI backend on :8000.
// Every request to /api/... is forwarded to the backend (with the /api prefix
// stripped) so the browser only ever talks to one origin — no CORS headaches.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
