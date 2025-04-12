const { app, BrowserWindow, dialog, shell, ipcMain, Tray, Menu } = require('electron');
const path = require('path');
const axios = require('axios');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let tray;
let backendProcess = null;
const BACKEND_PORT = 8001;
const BACKEND_URL = `http://localhost:${BACKEND_PORT}`;

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    minWidth: 600,
    minHeight: 400,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  await mainWindow.loadFile('index.html');

  const alreadyRunning = await checkBackendStatus();
  if (!alreadyRunning) {
    startBackendServer();
  }

  // 🔌 IPC HANDLERS

  ipcMain.handle('select-folders', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory', 'multiSelections']
    });
    return result.canceled ? [] : result.filePaths;
  });

  ipcMain.handle('index-folders', async (event, folders) => {
    try {
      const response = await axios.post(`${BACKEND_URL}/index`, { folders });
      const indexedFolders = response.data.indexed_folders || [];
      mainWindow.webContents.send('update-indexed-folders', indexedFolders);
      return { indexed_folders: indexedFolders };
    } catch (error) {
      console.error('Error indexing folders:', error);
      return { indexed_folders: [] };
    }
  });

  ipcMain.handle('search-documents', async (event, query) => {
    try {
      const response = await axios.post(`${BACKEND_URL}/search`, { query });
      return response.data.results || [];
    } catch (error) {
      console.error('Search error:', error);
      return [];
    }
  });

  ipcMain.handle('get-summary', async (event, filePath) => {
    try {
      const response = await axios.post(`${BACKEND_URL}/summary`, { file_path: filePath });
      return {
        file_path: filePath,
        title: path.basename(filePath),
        content: response.data.summary || 'No summary available.'
      };
    } catch (error) {
      console.error('Summary error:', error);
      throw error;
    }
  });

  ipcMain.handle('get-related', async (event, filePath) => {
    try {
      const response = await axios.post(`${BACKEND_URL}/related`, { file_path: filePath });
      return response.data.related || [];
    } catch (error) {
      console.error('Related error:', error);
      return [];
    }
  });

  ipcMain.handle('open-file', async (event, filePath) => {
    try {
      await shell.openPath(filePath);
    } catch (error) {
      console.error('File open error:', error);
    }
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});

async function checkBackendStatus() {
  try {
    const res = await axios.get(`${BACKEND_URL}/status`, { timeout: 1000 });
    if (res.status === 200) {
      console.log('✅ Backend server already running.');
      return true;
    }
  } catch (err) {
    console.log('❌ Backend not running.');
  }
  return false;
}

function startBackendServer() {
  const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';
  const backendPath = path.join(__dirname, '..', 'backend');

  if (!fs.existsSync(backendPath)) {
    dialog.showErrorBox('Error', `Backend not found at ${backendPath}`);
    return;
  }

  backendProcess = spawn(pythonCommand, [
    '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', BACKEND_PORT
  ], {
    cwd: backendPath,
    stdio: 'pipe'
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`Backend: ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`Backend error: ${data}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
  });
}
