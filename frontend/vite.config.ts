import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, /api requests are proxied to the FastAPI server so the browser sees one origin.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom", "@tanstack/react-query"],
          ui: ["@base-ui/react", "lucide-react", "sonner"],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: { "/api": process.env.SPOTIFREE_API_URL ?? "http://localhost:8000" },
  },
});
