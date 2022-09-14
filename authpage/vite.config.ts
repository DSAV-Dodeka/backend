import { defineConfig } from 'vite'
import { resolve } from 'path'
import react from '@vitejs/plugin-react'
import wasm from "vite-plugin-wasm";
import topLevelAwait from "vite-plugin-top-level-await";

// https://vitejs.dev/config/
export default defineConfig({
  base: "/credentials/",
  plugins: [
      react(),
      wasm(),
      topLevelAwait()
  ],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        register: resolve(__dirname, 'register/index.html')
      }
    },
    outDir: '../src/apiserver/resources/static/credentials'
  },
  server: {
    port: 4243
  }
})

