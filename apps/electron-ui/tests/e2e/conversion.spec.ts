/**
 * E2E test: import images from inputs/transformation_digital through the full
 * hand2notes pipeline and assert that Markdown output is generated.
 *
 * The test launches the real Electron app (which spawns its own Python backend).
 * The native file-dialog IPC handler is replaced before images are selected so
 * the test can inject fixed file paths without human interaction.
 *
 * Prerequisite: `npm run build` must be run before executing this suite.
 */

import { test, expect, _electron as electron } from '@playwright/test';
import type { ElectronApplication } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const REPO_ROOT   = path.resolve(__dirname, '../../../../');
const IMAGE_DIR   = path.join(REPO_ROOT, 'inputs', 'transformation_digital');
const OUTPUT_DIR  = path.join(REPO_ROOT, 'outputs');
const MAIN_JS     = path.resolve(__dirname, '../../dist-electron/main/index.js');
const CONFIG_DIR  = path.join(os.homedir(), '.config', 'hand2notes');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function collectMarkdownFiles(dir: string): string[] {
  const results: string[] = [];
  const walk = (d: string) => {
    for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith('.md')) results.push(full);
    }
  };
  if (fs.existsSync(dir)) walk(dir);
  return results;
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------
test.describe('transformation_digital conversion', () => {
  let savedConfig: string | null = null;
  let app: ElectronApplication | null = null;

  test.beforeAll(() => {
    // Persist current config so we can restore it after the suite.
    if (fs.existsSync(CONFIG_FILE)) {
      savedConfig = fs.readFileSync(CONFIG_FILE, 'utf-8');
    }
    // Write a minimal config that points the vault at outputs/.
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    fs.writeFileSync(
      CONFIG_FILE,
      JSON.stringify({
        vault_root: OUTPUT_DIR,
        folder_template: '{{notebook}}/{{name}}',
        export_mode: 'overwrite',
      }, null, 2),
    );
  });

  test.afterAll(async () => {
    await app?.close().catch(() => {});
    // Restore original config.
    if (savedConfig !== null) {
      fs.writeFileSync(CONFIG_FILE, savedConfig);
    } else if (fs.existsSync(CONFIG_FILE)) {
      fs.unlinkSync(CONFIG_FILE);
    }
  });

  // -------------------------------------------------------------------------
  test('full pipeline: import → OCR → Markdown', async () => {
    // Collect test images
    const images = fs.readdirSync(IMAGE_DIR)
      .filter(f => /\.(jpe?g|png|heic)$/i.test(f))
      .sort()
      .map(f => path.join(IMAGE_DIR, f));

    expect(images.length, `No images found in ${IMAGE_DIR}`).toBeGreaterThan(0);
    expect(fs.existsSync(MAIN_JS), `Build artifact missing: ${MAIN_JS} — run 'npm run build' first`).toBe(true);

    // Launch Electron; the main process will spawn the Python backend.
    app = await electron.launch({
      args: [MAIN_JS],
      cwd: path.resolve(__dirname, '../../'),
      env: { ...process.env, NODE_ENV: 'test', ELECTRON_IS_DEV: '0' },
    });

    const page = await app.firstWindow();
    await page.waitForLoadState('domcontentloaded');

    // Replace the native file-dialog handler so we can inject paths in CI.
    await app.evaluate(({ ipcMain }, paths) => {
      ipcMain.removeHandler('dialog:open-files');
      ipcMain.handle('dialog:open-files', () => paths);
    }, images);

    // ── Import screen ────────────────────────────────────────────────────────
    await expect(page.locator('h1')).toContainText('Import Notebook Pages', {
      timeout: 90_000,   // backend startup + model initialisation
    });

    await page.fill('input[placeholder*="CS101"]',          'Transformation Digital');
    await page.fill('input[placeholder*="Computer Science"]', 'E2E Test Notebook');

    await page.click('button:has-text("+ Add images")');

    // All images must appear in the selection list before submitting.
    await expect(page.locator('form ul li')).toHaveCount(images.length, {
      timeout: 20_000,
    });

    // ── Pipeline ─────────────────────────────────────────────────────────────
    await page.click('button:has-text("Start Processing")');

    await expect(page.locator('h1')).toContainText('Processing', { timeout: 30_000 });

    // Wait for all stages to complete — generous timeout for OCR + layout models.
    await expect(page.getByText('Export complete')).toBeVisible({
      timeout: 18 * 60_000,
    });

    // ── Output assertion ─────────────────────────────────────────────────────
    // The vault writer creates: <vault_root>/<notebook>/<name>/notes.md
    // based on the folder_template "{{notebook}}/{{name}}".
    const expectedNotebook = 'E2E Test Notebook';
    const expectedName     = 'Transformation Digital';
    const expectedMd = path.join(OUTPUT_DIR, expectedNotebook, expectedName, 'notes.md');

    expect(
      fs.existsSync(expectedMd),
      `Expected vault output at:\n  ${expectedMd}\n\nAll .md files found:\n  ${collectMarkdownFiles(OUTPUT_DIR).join('\n  ')}`,
    ).toBe(true);

    const content = fs.readFileSync(expectedMd, 'utf-8');
    expect(content.length, 'notes.md should not be empty').toBeGreaterThan(0);

    console.log(`\n✓ Vault output written to: ${expectedMd}`);
    console.log(`  Content length: ${content.length} bytes`);
  });
});
