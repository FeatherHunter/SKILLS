'use strict';

// 由 bin/dsh-harness-desktop.js 调用的 Electron 主进程脚本：
// 用 shell.writeShortcutLink（Windows 原生 .lnk）在桌面创建「桌面版」快捷方式。
// 参数：最后一个 argv = npm 包目录（内含 node_modules/electron）。
// 目标：包内的 electron.exe + 包目录（启动即开发模式，体验与 exe 一致）。

const { app, shell } = require('electron');
const path = require('path');

app.whenReady().then(() => {
  const pkgDir = process.argv[process.argv.length - 1];
  const electronExe = path.join(pkgDir, 'node_modules', 'electron', 'dist', 'electron.exe');
  const lnkPath = path.join(app.getPath('desktop'), '桌面版.lnk');
  const ok = shell.writeShortcutLink(lnkPath, 'create', {
    target: electronExe,
    args: '"' + pkgDir + '"',
    cwd: pkgDir,
    description: 'DSH 桌面版',
    icon: electronExe,
    iconIndex: 0,
  });
  console.log(ok ? 'SHORTCUT_OK ' + lnkPath : 'SHORTCUT_FAIL');
  app.exit(ok ? 0 : 1);
});
