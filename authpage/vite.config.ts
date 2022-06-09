import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  base: "/credentials/",
  plugins: [react()],
  build: {
    outDir: '../src/dodekaserver/resources/static/credentials'
  },
  server: {
    port: 4243
  }
})

