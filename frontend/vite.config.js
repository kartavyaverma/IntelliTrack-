import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // The API's CORS rules allow only port 5173. Fail loudly if it's taken
  // instead of silently moving to 5174, where every API call would fail.
  server: { port: 5173, strictPort: true },
})
