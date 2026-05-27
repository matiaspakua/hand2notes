import path from 'path';
import { fileURLToPath } from 'url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import electron from 'vite-plugin-electron/simple';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: 'src/renderer',
  resolve: {
    alias: { '@renderer': path.resolve(__dirname, 'src/renderer') },
  },
  plugins: [
    react(),
    electron({
      main: {
        entry: path.resolve(__dirname, 'src/main/index.ts'),
        vite: { build: { outDir: path.resolve(__dirname, 'dist-electron/main') } },
      },
      preload: {
        input: path.resolve(__dirname, 'src/preload/index.ts'),
        vite: { build: { outDir: path.resolve(__dirname, 'dist-electron/preload') } },
      },
    }),
  ],
  build: {
    outDir: path.resolve(__dirname, 'dist-electron/renderer'),
    emptyOutDir: true,
  },
});
