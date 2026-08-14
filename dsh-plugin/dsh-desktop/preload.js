'use strict';

// 启动页（boot.html）与主进程之间的最小桥：只暴露必要方法，不放开 Node 能力
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('dshDesktop', {
  getStatus: () => ipcRenderer.invoke('dsh-desktop:status'),
  onStatus: (cb) => ipcRenderer.on('dsh-desktop:status', (_event, status) => cb(status)),
  restart: () => ipcRenderer.invoke('dsh-desktop:restart'),
  retryInstall: () => ipcRenderer.invoke('dsh-desktop:retry-install'),
  quit: () => ipcRenderer.invoke('dsh-desktop:quit'),
  // 手动窗口拖拽 + 窗口控制（页面注入的标题栏带/自绘按钮使用；send 通道低延迟）
  dragStart: () => ipcRenderer.send('dsh-desktop:drag-start'),
  dragMove: (dx, dy) => ipcRenderer.send('dsh-desktop:drag-move', dx, dy),
  dragEnd: () => ipcRenderer.send('dsh-desktop:drag-end'),
  toggleMaximize: () => ipcRenderer.invoke('dsh-desktop:toggle-maximize'),
  minimize: () => ipcRenderer.invoke('dsh-desktop:minimize'),
  close: () => ipcRenderer.invoke('dsh-desktop:close'),
});
