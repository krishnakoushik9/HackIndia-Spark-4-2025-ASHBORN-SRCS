const { contextBridge, ipcRenderer } = require('electron');

// Expose IPC API to renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // Folder selection and indexing
  selectFolders: () => ipcRenderer.invoke('select-folders'),
  indexFolders: (folders) => ipcRenderer.invoke('index-folders', folders),
  
  // Document search and retrieval
  searchDocuments: (query) => ipcRenderer.invoke('search-documents', query),
  getSummary: (filePath) => ipcRenderer.invoke('get-summary', filePath),
  getRelated: (filePath) => ipcRenderer.invoke('get-related', filePath),
  openFile: (filePath) => ipcRenderer.invoke('open-file', filePath),
  
  // Receive events from main process
  onUpdateIndexedFolders: (callback) => {
    ipcRenderer.on('update-indexed-folders', (_, folders) => callback(folders));
    return () => {
      ipcRenderer.removeAllListeners('update-indexed-folders');
    };
  }
});