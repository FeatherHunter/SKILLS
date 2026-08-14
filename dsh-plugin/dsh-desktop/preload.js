'use strict';

// 启动页（boot.html）与主进程之间的最小桥：只暴露 4 个方法，不放开 Node 能力
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('dshDesktop', {
  getStatus: () => ipcRenderer.invoke('dsh-desktop:status'),
  onStatus: (cb) => ipcRenderer.on('dsh-desktop:status', (_event, status) => cb(status)),
  restart: () => ipcRenderer.invoke('dsh-desktop:restart'),
  quit: () => ipcRenderer.invoke('dsh-desktop:quit'),
});
