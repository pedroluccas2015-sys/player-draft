import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
      "/proxy-image": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
      // NOVA REGRA: Escudos dos Clubes
      "/proxy-team": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
      // NOVA REGRA: Logos dos Torneios/Ligas
      "/proxy-tournament": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
});
