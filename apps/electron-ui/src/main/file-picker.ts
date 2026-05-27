/**
 * Native file picker dialog for the Electron main process.
 * Exposed to the renderer via contextBridge in preload/index.ts.
 */
import { BrowserWindow, dialog } from 'electron';

export async function openImagePicker(win: BrowserWindow): Promise<string[]> {
  const result = await dialog.showOpenDialog(win, {
    title: 'Select notebook page images',
    properties: ['openFile', 'multiSelections'],
    filters: [
      { name: 'Images', extensions: ['jpg', 'jpeg', 'png'] },
    ],
  });

  if (result.canceled) {
    return [];
  }
  return result.filePaths;
}
