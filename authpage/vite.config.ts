import {defineConfig} from 'vite'
import { resolve } from 'path'
import react from '@vitejs/plugin-react'
import wasm from "vite-plugin-wasm";
import topLevelAwait from "vite-plugin-top-level-await";
import svgr from "vite-plugin-svgr"

// https://vitejs.dev/config/
export default defineConfig({
  base: "/credentials/",
  plugins: [
      react(),
      wasm(),
      topLevelAwait(),
      svgr()
  ],
  build: {
    target: "es2016",
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        register: resolve(__dirname, 'register/index.html'),
        email: resolve(__dirname, 'email/index.html'),
        reset: resolve(__dirname, 'reset/index.html')
      }
    },
    outDir: '../src/apiserver/resources/static/credentials'
  },
  server: {
    port: 4244
  }
})

