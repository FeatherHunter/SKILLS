#!/usr/bin/env node
'use strict';

// dsh-harness-desktop 的命令行入口（npm 包形态）
//
// 用法：
//   dsh-harness-desktop shortcut
//     在桌面创建「桌面版」快捷方式：指向包内的 electron 运行时 + 本包目录。
//     之后双击快捷方式即可启动（无需开终端），体验与便携 exe 一致。
//
// 注意：快捷方式依赖 electron 运行时（开发依赖），请先在包目录执行
// `npm install` 补齐后再运行本命令。

const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const pkgDir = path.join(__dirname, '..');
const electronExe = path.join(pkgDir, 'node_modules', 'electron', 'dist', 'electron.exe');

function usage() {
  console.log('dsh-harness-desktop — 创建桌面快捷方式');
  console.log('');
  console.log('用法: dsh-harness-desktop shortcut');
  console.log('  在桌面创建「桌面版」快捷方式（指向本包 + electron 运行时）');
}

function createShortcut() {
  if (!fs.existsSync(electronExe)) {
    console.error('未找到 electron 运行时（' + electronExe + '）。');
    console.error('请先在包目录执行 npm install 补齐开发依赖，再重新运行本命令。');
    process.exit(1);
  }
  // 用 electron.exe 跑一个 Electron 主进程脚本，走 shell.writeShortcutLink
  // （Windows 原生 .lnk 创建，无 COM/编码问题）
  const r = spawnSync(electronExe, [path.join(__dirname, 'shortcut-main.js'), pkgDir], {
    stdio: 'inherit',
    timeout: 60000,
  });
  if (r.status === 0) {
    console.log('桌面已创建「桌面版」快捷方式，双击即可启动。');
  } else {
    console.error('创建失败（exit ' + r.status + '），可尝试手动：右键 exe → 发送到 → 桌面快捷方式。');
    process.exit(r.status || 1);
  }
}

const cmd = process.argv[2];
if (cmd === 'shortcut') {
  createShortcut();
} else {
  usage();
}
