import { defineConfig } from "vite";

export default defineConfig({
  server: {
    proxy: {
      "/documents": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
      "/rag": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
