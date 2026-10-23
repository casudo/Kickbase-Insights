import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// `npm run dev` proxies the API to a locally running backend (python -m kbi)
const backend = process.env.KBI_BACKEND_URL ?? "http://localhost:8000"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": "/src" },
  },
  server: {
    port: 5173,
    proxy: { "/api": { target: backend, changeOrigin: true } },
  },
  build: {
    target: "es2022",
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        // Charts are only needed on a few pages and stay out of the initial download. The framework
        // changes rarely, so it gets a chunk of its own that browsers keep cached across updates.
        manualChunks(id) {
          if (!id.includes("node_modules")) return
          if (/node_modules[\/](recharts|d3-[^\/]+|victory-vendor|decimal\.js-light|react-redux|@reduxjs|immer|reselect|redux|es-toolkit|eventemitter3|tiny-invariant)[\/]/.test(id))
            return "charts"
          if (/node_modules[\/](react|react-dom|scheduler|react-router|cookie|set-cookie-parser|@tanstack[\/](react-query|query-core))[\/]/.test(id))
            return "vendor"
        },
      },
    },
  },
})
