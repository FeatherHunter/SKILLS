'use strict';

// electron-builder afterPack 钩子：
// 官方 filter 会排除 extraResources 里的「根 node_modules」（filter.js:42），
// 导致捆绑的 npm 依赖丢失（Cannot find module 'graceful-fs'）。
// 打包完成后用原生复制把 node_modules 补回 resources/runtime/npm/。

const fs = require('fs');
const path = require('path');

exports.default = async function afterPack(context) {
  const { appOutDir, packager } = context;
  const projectDir = packager.projectDir;
  const src = path.join(projectDir, 'runtime-resources', 'npm', 'node_modules');
  const dest = path.join(appOutDir, 'resources', 'runtime', 'npm', 'node_modules');
  if (!fs.existsSync(src)) {
    console.log('[after-pack] 警告: 源 node_modules 不存在 ' + src);
    return;
  }
  if (fs.existsSync(dest)) {
    console.log('[after-pack] node_modules 已存在，跳过 ' + dest);
    return;
  }
  fs.cpSync(src, dest, { recursive: true });
  const count = fs.readdirSync(dest).length;
  console.log(`[after-pack] 已补回 npm node_modules（${count} 个包）→ ${dest}`);
};
