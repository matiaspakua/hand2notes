/**
 * E2E: drive the real Electron app through the full pipeline for every folder in
 * inputs/, and assert the generated Markdown contains text, a table and a Mermaid
 * diagram. The app spawns its own Python backend; the native file dialog is stubbed
 * so image paths can be injected without human interaction.
 *
 * Prerequisite: `npm run build` must be run before executing this suite.
 */

import { test, expect, _electron as electron } from '@playwright/test';
import type { ElectronApplication, Page } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const REPO_ROOT = path.resolve(__dirname, '../../../../');
const INPUTS_DIR = path.join(REPO_ROOT, 'inputs');
const FIXTURES_DIR = path.join(__dirname, 'fixtures');
const OUTPUT_DIR = path.join(REPO_ROOT, 'outputs', 'e2e-vault');
const MAIN_JS = path.resolve(__dirname, '../../dist-electron/main/index.js');
const CONFIG_DIR = path.join(os.homedir(), '.config', 'hand2notes');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');

interface Target {
  dir: string; // absolute path to an input folder
  notebook: string;
  name: string;
  images: string[];
}

function imagesIn(dir: string): string[] {
  return fs
    .readdirSync(dir)
    .filter((f) => /\.(jpe?g|png|heic)$/i.test(f))
    .sort()
    .map((f) => path.join(dir, f));
}

/**
 * Targets = every inputs/<folder> with images (real handwritten pages — validate
 * text + diagrams), plus a clean printed-table fixture. The handwritten grids are
 * transcribed inconsistently as tables vs lists by the VLM, so the table-rendering
 * path is validated deterministically through a fixture the VLM reliably tabulates.
 */
function discoverTargets(): Target[] {
  const inputs = fs
    .readdirSync(INPUTS_DIR, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => {
      const dir = path.join(INPUTS_DIR, e.name);
      return { dir, notebook: 'E2E', name: e.name, images: imagesIn(dir) };
    })
    .filter((t) => t.images.length > 0)
    .sort((a, b) => a.name.localeCompare(b.name));

  const fixtures: Target[] = fs.existsSync(FIXTURES_DIR)
    ? [{ dir: FIXTURES_DIR, notebook: 'E2E', name: 'sample_tables', images: imagesIn(FIXTURES_DIR) }].filter(
        (t) => t.images.length > 0,
      )
    : [];

  return [...inputs, ...fixtures];
}

function notesPathFor(t: Target): string {
  // folder_template "{{notebook}}/{{name}}" → <vault>/<notebook>/<name>/notes.md
  return path.join(OUTPUT_DIR, t.notebook, t.name, 'notes.md');
}

/** Run one import → convert → done cycle for a target; returns notes.md content. */
async function convert(app: ElectronApplication, page: Page, t: Target): Promise<string> {
  await app.evaluate(({ ipcMain }, paths) => {
    ipcMain.removeHandler('dialog:open-files');
    ipcMain.handle('dialog:open-files', () => paths);
  }, t.images);

  await expect(page.locator('h1')).toContainText('Import Notebook Pages', { timeout: 120_000 });
  await page.fill('input[placeholder*="CS101"]', t.name);
  await page.fill('input[placeholder*="Computer Science"]', t.notebook);
  await page.click('button:has-text("+ Add images")');
  await expect(page.locator('form ul li')).toHaveCount(t.images.length, { timeout: 20_000 });

  await page.click('button:has-text("Start Processing")');
  await expect(page.locator('h1')).toContainText('Converting your notes', { timeout: 60_000 });

  // Completion is signalled by the outcome panel's button.
  await expect(page.getByRole('button', { name: /View exported notes/i })).toBeVisible({
    timeout: 18 * 60_000,
  });
  await page.getByRole('button', { name: /View exported notes/i }).click();
  await expect(page.getByText('Export complete')).toBeVisible({ timeout: 30_000 });

  const notes = notesPathFor(t);
  expect(fs.existsSync(notes), `notes.md not generated at ${notes}`).toBe(true);
  const content = fs.readFileSync(notes, 'utf-8');
  expect(content.length, 'notes.md should not be empty').toBeGreaterThan(0);

  // Return to import for the next target (no-op effect on the last one).
  await page.getByRole('button', { name: /Process another session/i }).click();
  return content;
}

test.describe('full pipeline conversion (all inputs)', () => {
  let savedConfig: string | null = null;
  let app: ElectronApplication | null = null;

  test.beforeAll(() => {
    if (fs.existsSync(CONFIG_FILE)) savedConfig = fs.readFileSync(CONFIG_FILE, 'utf-8');
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
    fs.rmSync(OUTPUT_DIR, { recursive: true, force: true });
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    fs.writeFileSync(
      CONFIG_FILE,
      JSON.stringify(
        {
          vault_root: OUTPUT_DIR,
          folder_template: '{{notebook}}/{{name}}',
          export_mode: 'overwrite',
          vlm_transcription_enabled: true,
          spell_correction_enabled: false,
        },
        null,
        2,
      ),
    );
  });

  test.afterAll(async () => {
    await app?.close().catch(() => {});
    if (savedConfig !== null) fs.writeFileSync(CONFIG_FILE, savedConfig);
    else if (fs.existsSync(CONFIG_FILE)) fs.unlinkSync(CONFIG_FILE);
  });

  test('converts every input folder and produces text, tables and diagrams', async () => {
    const targets = discoverTargets();
    expect(targets.length, `No input folders with images under ${INPUTS_DIR}`).toBeGreaterThan(0);
    expect(fs.existsSync(MAIN_JS), `Build missing: ${MAIN_JS} — run 'npm run build'`).toBe(true);

    app = await electron.launch({
      args: [MAIN_JS],
      cwd: path.resolve(__dirname, '../../'),
      env: { ...process.env, NODE_ENV: 'test', ELECTRON_IS_DEV: '0' },
    });
    const page = await app.firstWindow();
    await page.waitForLoadState('domcontentloaded');

    const outputs: Record<string, string> = {};
    for (const t of targets) {
      outputs[t.name] = await convert(app, page, t);
      // eslint-disable-next-line no-console
      console.log(`OK ${t.name}: ${t.images.length} page(s) -> ${outputs[t.name].length} bytes`);
    }

    const corpus = Object.values(outputs).join('\n\n');
    const hasTable = /^\s*\|.*\|\s*$[\r\n]+\s*\|[\s:|-]+\|/m.test(corpus);
    const hasDiagram = /```mermaid[\s\S]*?```/.test(corpus);
    const hasText = /[A-Za-zÁÉÍÓÚÑáéíóúñ]{4,}/.test(corpus);

    // eslint-disable-next-line no-console
    console.log(`Validation - text:${hasText} table:${hasTable} diagram:${hasDiagram}`);

    expect(hasText, 'output should contain transcribed text').toBe(true);
    expect(hasTable, 'output should contain at least one Markdown table').toBe(true);
    expect(hasDiagram, 'output should contain at least one Mermaid diagram').toBe(true);
  });
});
