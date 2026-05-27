import { contextBridge, ipcRenderer } from 'electron';

/** OS-level bridge exposed to the renderer as `window.h2n`. */
const api = {
  /** Port the Python FastAPI backend is listening on (null until ready). */
  getApiPort: (): Promise<number | null> => ipcRenderer.invoke('api:get-port'),
  /** Open the native file picker; returns selected absolute image paths. */
  openImageFiles: (): Promise<string[]> => ipcRenderer.invoke('dialog:open-files'),
};

contextBridge.exposeInMainWorld('h2n', api);

export type H2nBridge = typeof api;
