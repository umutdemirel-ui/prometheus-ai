const {contextBridge,ipcRenderer} = require('electron');
// No generic IPC, Node.js, filesystem, or credential access is exposed to the renderer.
contextBridge.exposeInMainWorld('prometheusDesktop', Object.freeze({
  chooseDirectory: () => ipcRenderer.invoke('prometheus:choose-directory'),
  execute: action => ipcRenderer.invoke('prometheus:execute-tool', action),
  clearDirectory: () => ipcRenderer.invoke('prometheus:clear-directory')
}));
