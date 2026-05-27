import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { app, BrowserWindow, dialog, ipcMain } from 'electron';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

let pythonProc: ChildProcessWithoutNullStreams | null = null;
let apiPort: number | null = null;
let mainWindow: BrowserWindow | null = null;

/**
 * Spawn the Python FastAPI backend and resolve once it announces its port
 * on stdout as `HAND2NOTES_PORT=<port>` (see hand2notes.api.__main__).
 */
function startBackend(): Promise<number> {
  return new Promise((resolve, reject) => {
    const repoRoot = path.resolve(app.getAppPath(), '..', '..');
    pythonProc = spawn('uv', ['run', '--package', 'hand2notes-api', 'python', '-m', 'hand2notes.api'], {
      cwd: repoRoot,
      env: process.env,
    });

    const onData = (chunk: Buffer) => {
      const text = chunk.toString();
      const match = text.match(/HAND2NOTES_PORT=(\d+)/);
      if (match) {
        apiPort = Number(match[1]);
        pythonProc?.stdout.off('data', onData);
        resolve(apiPort);
      }
    };
    pythonProc.stdout.on('data', onData);
    pythonProc.stderr.on('data', (c: Buffer) => console.error('[python-api]', c.toString()));
    pythonProc.on('error', reject);
    pythonProc.on('exit', (code) => console.error(`[python-api] exited with code ${code}`));
  });
}

async function createWindow(): Promise<void> {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'index.mjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const devServer = process.env.VITE_DEV_SERVER_URL;
  if (devServer) {
    await mainWindow.loadURL(devServer);
  } else {
    await mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
  }
}

app.whenReady().then(async () => {
  ipcMain.handle('api:get-port', () => apiPort);
  ipcMain.handle('dialog:open-files', async () => {
    const result = await dialog.showOpenDialog({
      title: 'Select notebook page images',
      properties: ['openFile', 'multiSelections'],
      filters: [{ name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'heic'] }],
    });
    return result.canceled ? [] : result.filePaths;
  });

  try {
    await startBackend();
  } catch (err) {
    console.error('Failed to start Python backend:', err);
    await dialog.showErrorBox(
      'Backend startup failed',
      `Unable to start the Python backend. Check the terminal for details.\n\n${String(err)}`,
    );
    return;
  }
  await createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) void createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  pythonProc?.kill();
});
