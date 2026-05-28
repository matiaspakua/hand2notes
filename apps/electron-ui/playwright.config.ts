import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 20 * 60 * 1000,        // 20 min — OCR models may download on first run
  expect: { timeout: 15 * 60 * 1000 },
  workers: 1,                      // Electron apps can't run in parallel
  retries: 0,
  reporter: [['line'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
});
