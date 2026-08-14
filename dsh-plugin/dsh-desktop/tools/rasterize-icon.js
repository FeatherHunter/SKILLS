'use strict';

// 用 Electron 离屏渲染把 tools/icon-app.html（矢量鱼形图标）栅格化为
// build/icon.png（512x512），供 electron-builder 自动转成 .ico/.icns。
// 用法：npm run icon

const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

app.whenReady().then(async () => {
  try {
    const win = new BrowserWindow({
      width: 512,
      height: 512,
      show: false,
      frame: false,
      webPreferences: { offscreen: true },
    });
    await win.loadFile(path.join(__dirname, 'icon-app.html'));
    await new Promise((r) => setTimeout(r, 600));
    const img = await win.webContents.capturePage({ x: 0, y: 0, width: 512, height: 512 });
    const out = path.join(__dirname, '..', 'build', 'icon.png');
    fs.writeFileSync(out, img.toPNG());
    console.log('ICON_WRITTEN ' + out + ' (' + img.getSize().width + 'x' + img.getSize().height + ')');
    app.quit();
  } catch (e) {
    console.error('ICON_FAILED ' + e.message);
    app.exit(1);
  }
});
