import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(() => {
  const backend = process.env.VITE_API_URL || 'http://127.0.0.1:8000';
  const wsBackend = backend.replace(/^http/, 'ws');

  return {
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: backend,
          changeOrigin: true,
        },
        '/ws': {
          target: wsBackend,
          ws: true,
        },
      },
    },
  };
});
