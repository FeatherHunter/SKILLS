'use strict';

// ============================================================
// DSH 桌面版 · Electron 主进程（进程管家）
//
// 职责：
//   1. 后台拉起 DSH Web 服务（无终端窗口）
//   2. 等待服务就绪后，把页面嵌进桌面窗口（只看到页面，看不到命令）
//   3. 关闭窗口 / 退出应用时，把后台进程（DSH / npm 安装）一并杀掉
//
// 零依赖设计：
//   - 不要求系统安装 Node.js：Electron 自带完整 Node（ELECTRON_RUN_AS_NODE）
//   - 捆绑 npm（11MB，resources/runtime/npm）负责首次自动安装 DSH
//   - 装好后用内置 Node 直接运行 DSH（--expose-internals 是 HMR 插件要求）
//
// 环境变量（可选）：
//   DSH_DESKTOP_PORT        服务端口，默认 3080
//   DSH_DESKTOP_COMMAND     自定义启动命令（整行，按 shell 解析；设置后跳过内置运行时）
//   DSH_DESKTOP_REGISTRY    npm 镜像源（默认 registry.npmjs.org，国内可设 npmmirror）
//   DSH_DESKTOP_REINSTALL=1 强制重装 DSH 运行时（升级用）
//   DSH_DESKTOP_SMOKE=1     冒烟测试模式：页面就绪后自动退出（自动化验证）
//   DSH_DESKTOP_SHOT=1      截图模式：布局自检 + 存 PNG 后退出
// ============================================================

const { app, BrowserWindow, ipcMain, shell, nativeTheme } = require('electron');
const { spawn, spawnSync } = require('child_process');
const http = require('http');
const net = require('net');
const path = require('path');
const fs = require('fs');

// ---------- 配置 ----------
const DEFAULT_PORT = 3080;
const START_TIMEOUT_MS = 10 * 60 * 1000; // 首次安装/启动 DSH 包（数百 MB），放宽到 10 分钟
const POLL_INTERVAL_MS = 600;
const TITLEBAR_H = 40; // 顶部标题栏带高度：页面内容下移量 = WCO 按钮悬浮区高度

const PORT = Number(process.env.DSH_DESKTOP_PORT || DEFAULT_PORT);
const TARGET_URL = `http://127.0.0.1:${PORT}`;
const SMOKE = process.env.DSH_DESKTOP_SMOKE === '1';
const SHOT = process.env.DSH_DESKTOP_SHOT === '1'; // 截图调试模式：页面就绪后存 PNG 再退出
const [SHOT_W, SHOT_H] = (process.env.DSH_DESKTOP_SIZE || '1280x820').split('x').map(Number);

// ---------- 内置运行时（零系统依赖：不需要安装 Node.js） ----------
// Electron 自带完整 Node：ELECTRON_RUN_AS_NODE=1 时 exe 本身即 node。
// 捆绑 npm（仅 11MB）→ 首次运行自动 npm install @deepseek-ai/dsh 到用户目录 →
// 用内置 Node 直接跑 DSH（--expose-internals 是 DSH 的 HMR 插件要求）。
const RUNTIME_DIR = path.join(app.getPath('appData'), 'dsh-desktop', 'runtime');
const NPM_DIR = app.isPackaged
  ? path.join(process.resourcesPath, 'runtime', 'npm')
  : path.join(__dirname, 'runtime-resources', 'npm');
const NPM_CLI = path.join(NPM_DIR, 'bin', 'npm-cli.js');
const DSH_BIN = path.join(RUNTIME_DIR, 'node_modules', '@deepseek-ai', 'dsh', 'lib', 'bin.js');
const NODE_ENV = { ...process.env, ELECTRON_RUN_AS_NODE: '1' };

// 日志：dev 与打包后同一路径（%APPDATA%/dsh-desktop/dsh.log）
const logDir = path.join(app.getPath('appData'), 'dsh-desktop');
const logFile = path.join(logDir, 'dsh.log');
try { fs.mkdirSync(logDir, { recursive: true }); } catch { /* 忽略 */ }

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  try { fs.appendFileSync(logFile, line + '\n'); } catch { /* 忽略 */ }
  console.log(line); // dev 模式可见；打包后无控制台，只落日志文件
}

function tailLog(n = 20) {
  try {
    const lines = fs.readFileSync(logFile, 'utf8').split('\n').filter(Boolean);
    return lines.slice(-n).join('\n');
  } catch { return ''; }
}

// ---------- 命令行工具模式：创建桌面快捷方式 ----------
// 用法：dsh-harness-desktop-1.0.0-x64.exe --install-shortcut
// 在桌面创建指向本 exe 的「桌面版」快捷方式后立即退出。
// 便携版：electron-builder 注入 PORTABLE_EXECUTABLE_FILE 指向用户放置的原始 exe。
// 实现：Electron 原生 shell.writeShortcutLink（Windows .lnk，无 COM/编码坑）。
const INSTALL_SHORTCUT = process.argv.includes('--install-shortcut');

function makeShortcut() {
  const target = process.env.PORTABLE_EXECUTABLE_FILE || process.execPath;
  if (!fs.existsSync(target)) {
    log('SHORTCUT_FAIL: 目标不存在 ' + target);
    console.log('SHORTCUT_FAIL target missing: ' + target);
    app.exit(1);
    return;
  }
  const lnkPath = path.join(app.getPath('desktop'), '桌面版.lnk');
  try {
    const ok = shell.writeShortcutLink(lnkPath, 'create', {
      target,
      cwd: path.dirname(target),
      description: 'DSH 桌面版',
      icon: target,
      iconIndex: 0,
    });
    if (ok) {
      log('已创建桌面快捷方式 → ' + lnkPath);
      console.log('SHORTCUT_OK ' + lnkPath);
      app.exit(0);
    } else {
      log('SHORTCUT_FAIL: writeShortcutLink 返回 false');
      console.log('SHORTCUT_FAIL writeShortcutLink=false');
      app.exit(1);
    }
  } catch (e) {
    log('SHORTCUT_FAIL: ' + e.message);
    console.log('SHORTCUT_FAIL ' + e.message);
    app.exit(1);
  }
}

// ---------- 状态 ----------
let child = null;        // DSH 子进程
let installProc = null;  // npm install 子进程（同样纳入「关窗即杀」）
let runtimeBusy = false; // npm 安装进行中（防重入）
let startedByUs = false; // 本次是否由我们拉起（决定退出时杀不杀）
let quitting = false;
let aborting = false;    // 主动清理中（restart/quit）：忽略子进程退出回调，防错误页闪现
let mainWindow = null;
let currentPhase = 'starting';
let lastStatus = { phase: 'starting', message: '', log: '' };
let smokeDone = false;
let shotDone = false;

// ---------- 子进程管理 ----------
// 自定义命令（高级用户）优先；否则走内置运行时
function customCommand() {
  return process.env.DSH_DESKTOP_COMMAND || null;
}

function spawnDsh() {
  const custom = customCommand();
  if (custom) {
    log('拉起命令: ' + custom);
    child = spawn(custom, {
      shell: true,                                  // Windows 经 cmd.exe、Unix 经 sh 执行
      windowsHide: true,
      detached: process.platform !== 'win32',
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, DSH_DESKTOP_PORT: String(PORT) },
    });
  } else {
    // 内置运行时：当前 exe 即 Node（ELECTRON_RUN_AS_NODE），直接跑安装好的 DSH
    log('拉起内置 DSH: ' + DSH_BIN + ' --port ' + PORT);
    child = spawn(process.execPath, ['--expose-internals', DSH_BIN, 'web', '--port', String(PORT)], {
      windowsHide: true,
      detached: process.platform !== 'win32',
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...NODE_ENV, DSH_DESKTOP_PORT: String(PORT) },
    });
  }
  child.stdout.on('data', (d) => log('[dsh] ' + String(d).trim()));
  child.stderr.on('data', (d) => log('[dsh] ' + String(d).trim()));
  child.on('error', (err) => {
    log('启动失败: ' + err.message);
    onChildGone('DSH 启动失败：' + err.message);
  });
  child.on('exit', (code, signal) => {
    log(`DSH 子进程退出 code=${code} signal=${signal || ''}`);
    onChildGone(code === 0 ? 'DSH 服务已退出' : `DSH 服务异常退出（code=${code}${signal ? '，signal=' + signal : ''}）`);
  });
}

// 杀掉整棵进程树：Windows 用 taskkill /T（递归），Unix 杀整个进程组
function killTree(procRef) {
  const pid = procRef && procRef.pid;
  if (!pid) return;
  try {
    if (process.platform === 'win32') {
      spawnSync('taskkill', ['/pid', String(pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true });
    } else {
      try { process.kill(-pid, 'SIGTERM'); } catch { /* 忽略 */ }
      try { process.kill(pid, 'SIGTERM'); } catch { /* 忽略 */ }
      setTimeout(() => { try { process.kill(-pid, 'SIGKILL'); } catch { /* 忽略 */ } }, 3000).unref();
    }
  } catch (e) {
    log('杀进程失败: ' + e.message);
  }
}

// 退出/重启时统一清理：DSH + npm 安装进程（承诺：关窗即停，无孤儿进程）
function killAllChildren() {
  aborting = true; // 抑制被杀进程的 exit 回调（防错误页闪现）
  killTree(child);
  child = null;
  if (installProc) { killTree(installProc); installProc = null; }
  // 给子进程 exit 事件留出传播窗口，之后恢复正常回调
  setTimeout(() => { aborting = false; }, 800).unref();
}

// 子进程没了（意外退出 / 启动超时）：窗口还开着就回落到错误页
function onChildGone(message) {
  if (aborting || quitting) return; // 主动清理中，忽略
  const wasOurs = startedByUs;
  const deadChild = child; // 先抓引用再置空：超时场景需要真正杀掉残留 DSH
  child = null;
  startedByUs = false;
  if (wasOurs && deadChild) killTree(deadChild);
  if (quitting || !mainWindow || mainWindow.isDestroyed()) return;
  const hint = errorHint(tailLog(30));
  log('进入错误页: ' + message + (hint ? ' [' + hint + ']' : ''));
  sendStatus('error', message + (hint ? '\n\n' + hint : ''), tailLog(30));
}

// 把常见底层报错翻译成人类能懂的原因（供错误页展示）
function errorHint(logTail) {
  if (!logTail) return '';
  if (/EADDRINUSE|address already in use/i.test(logTail)) {
    return `推测原因：端口 ${PORT} 已被其他程序占用。请关闭占用程序，或用环境变量 DSH_DESKTOP_PORT 换一个端口。`;
  }
  if (/ENOTFOUND|ECONNREFUSED|ECONNRESET|ETIMEDOUT|EAI_AGAIN|fetch failed|network request failed/i.test(logTail)) {
    return '推测原因：网络问题 —— 无法访问 npm 源下载 DSH。请检查网络或代理后点「重新启动」。';
  }
  if (/不是内部或外部命令|not recognized|ENOENT/i.test(logTail)) {
    return '推测原因：启动命令不可用（自定义命令配置可能有误，或命令路径不存在）。';
  }
  return '';
}

// ---------- 端口探测 ----------
// 只认「真正的 DSH」：HTTP 200 且页面带 __DSH_BOOT__ 指纹（避免连到陌生服务）
function checkDsh(cb) {
  let done = false;
  const finish = (ok) => { if (!done) { done = true; cb(ok); } };
  const req = http.get(TARGET_URL, { timeout: 2500 }, (res) => {
    let body = '';
    res.setEncoding('utf8');
    res.on('data', (d) => {
      body += d;
      if (body.length >= 4096) { finish(body.includes('__DSH_BOOT__')); req.destroy(); }
    });
    res.on('end', () => finish(res.statusCode === 200 && body.includes('__DSH_BOOT__')));
    res.on('error', () => finish(false));
  });
  req.on('timeout', () => { req.destroy(); finish(false); });
  req.on('error', () => finish(false));
}

// 端口上「有没有任何服务在听」（TCP 探测，覆盖纯 TCP 服务）
function checkPort(cb) {
  const sock = net.connect({ port: PORT, host: '127.0.0.1' });
  sock.setTimeout(1500);
  let done = false;
  const finish = (ok) => { if (!done) { done = true; sock.destroy(); cb(ok); } };
  sock.once('connect', () => finish(true));
  sock.once('timeout', () => finish(false));
  sock.once('error', () => finish(false));
}

function waitForServer(deadline, onReady, onTimeout) {
  const tick = () => {
    checkDsh((ok) => {
      if (ok) return onReady();
      if (Date.now() > deadline) return onTimeout();
      const left = Math.max(1, Math.round((deadline - Date.now()) / 1000));
      sendStatus('waiting', `正在等待 DSH 启动…（${left}s 后超时，首次运行需下载 DSH 包）`);
      setTimeout(tick, POLL_INTERVAL_MS);
    });
  };
  tick();
}

// 确保 DSH 运行时已安装（内置 npm 自动安装，首次联网下载，之后离线可用）
function ensureRuntime(onDone) {
  if (runtimeBusy) {
    log('runtime: 已有安装进行中，忽略重复请求');
    return;
  }
  if (process.env.DSH_DESKTOP_REINSTALL !== '1' && fs.existsSync(DSH_BIN)) {
    log('runtime: DSH 已安装 ' + DSH_BIN);
    return onDone(true);
  }
  if (!fs.existsSync(NPM_CLI)) {
    log('runtime: 捆绑 npm 缺失 ' + NPM_CLI);
    sendStatus('error', '应用组件缺失（内置 npm 未找到），请重新下载完整版应用。', tailLog(10));
    return onDone(false);
  }
  const registry = process.env.DSH_DESKTOP_REGISTRY || 'https://registry.npmjs.org';
  log('runtime: 开始安装 DSH（npm install @deepseek-ai/dsh → ' + RUNTIME_DIR + '）');
  sendStatus('installing', '首次使用：正在下载并安装 DSH 运行时…\n需要联网，大包下载约几分钟；装好后即可离线使用。');
  runtimeBusy = true;
  installProc = spawn(process.execPath, [
    NPM_CLI, 'install', '--prefix', RUNTIME_DIR, '--no-audit', '--no-fund',
    '--loglevel', 'error', '--registry', registry, '@deepseek-ai/dsh',
  ], {
    windowsHide: true,
    detached: process.platform !== 'win32',
    stdio: ['ignore', 'pipe', 'pipe'],
    env: NODE_ENV,
  });
  installProc.stdout.on('data', (d) => log('[npm] ' + String(d).trim()));
  installProc.stderr.on('data', (d) => log('[npm] ' + String(d).trim()));
  let ticks = 0;
  const progress = setInterval(() => {
    ticks += 1;
    sendStatus('installing', `正在下载并安装 DSH 运行时…（已进行 ${ticks * 3}s，首次大包下载需要几分钟）`, tailLog(4));
  }, 3000);
  const settled = (ok) => {
    clearInterval(progress);
    runtimeBusy = false;
    installProc = null;
    onDone(ok);
  };
  installProc.on('error', (err) => {
    log('npm 启动失败: ' + err.message);
    settled(false);
  });
  installProc.on('exit', (code) => {
    const ok = code === 0 && fs.existsSync(DSH_BIN);
    log('npm install 结束 code=' + code + ' ok=' + ok);
    settled(ok);
  });
}

// ---------- 启动流程 ----------
function startup() {
  checkDsh((isDsh) => {
    if (isDsh) {
      // 端口上就是 DSH（比如用户手动开过）：直接连上，退出时【不】杀它
      startedByUs = false;
      log(`端口 ${PORT} 已有 DSH 实例，连接现有实例（退出不会停止它）`);
      sendStatus('ready', '已连接现有 DSH 实例');
      loadTarget();
      return;
    }
    // 端口有别的服务（不是 DSH）？明确提示，绝不乱连
    checkPort((anyService) => {
      if (anyService) {
        log(`端口 ${PORT} 被非 DSH 服务占用`);
        sendStatus('error',
          `端口 ${PORT} 被其他程序占用（检测到服务，但不是 DSH）。\n\n请关闭占用 ${PORT} 端口的程序后重试；\n或者用环境变量 DSH_DESKTOP_PORT 换一个端口。`,
          tailLog(10), { needPort: true });
        return;
      }
      const launch = () => {
        startedByUs = true;
        spawnDsh();
        const deadline = Date.now() + START_TIMEOUT_MS;
        sendStatus('waiting', '正在启动 DSH 服务…');
        waitForServer(deadline, () => {
          log('DSH 就绪: ' + TARGET_URL);
          sendStatus('ready', 'DSH 已就绪');
          loadTarget();
        }, () => {
          log('等待 DSH 就绪超时');
          onChildGone(`启动超时：${START_TIMEOUT_MS / 60000} 分钟内 DSH 未就绪，可点「重新启动」再试`);
        });
      };
      if (customCommand()) {
        launch(); // 高级模式：用户自定义命令（无需内置运行时）
      } else {
        ensureRuntime((ok) => {
          if (!ok) {
            onChildGone('DSH 运行时安装失败。\n请检查网络后点「重新启动」重试；\n国内网络可设环境变量 DSH_DESKTOP_REGISTRY=https://registry.npmmirror.com 使用镜像。');
            return;
          }
          launch();
        });
      }
    });
  });
}

function loadTarget() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.loadURL(TARGET_URL);
}

// ---------- 界面 ----------
function sendStatus(phase, message, logTail, extra) {
  currentPhase = phase;
  lastStatus = { phase, message: message || '', log: logTail || tailLog(20), ...(extra || {}) };
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('dsh-desktop:status', lastStatus);
  }
}

function createWindow() {
  const winOpts = {
    width: SHOT ? SHOT_W : 1280,
    height: SHOT ? SHOT_H : 820,
    minWidth: 940, minHeight: 600,
    title: 'DSH 桌面版',
    backgroundColor: '#0a0a0a',
    autoHideMenuBar: true,
    icon: path.join(__dirname, 'build', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  };
  if (process.platform === 'win32') {
    // 无原生标题栏。页面内容整体下移 TITLEBAR_H 后，右上角三个按钮
    // 悬浮在空白标题栏带上，不遮挡任何页面内容（见 polishTargetPage）
    winOpts.titleBarStyle = 'hidden';
    winOpts.titleBarOverlay = { color: '#0a0a0a', symbolColor: '#a1a1aa', height: TITLEBAR_H };
  } else if (process.platform === 'darwin') {
    winOpts.titleBarStyle = 'hiddenInset';
  }
  mainWindow = new BrowserWindow(winOpts);
  mainWindow.on('closed', () => { mainWindow = null; });

  // 页面里的外链一律交给系统浏览器，避免产生脱离生命周期的孤儿窗口
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.webContents.on('did-finish-load', () => {
    const url = mainWindow.webContents.getURL();
    if (url.startsWith(TARGET_URL)) {
      polishTargetPage();
      if (SMOKE && !smokeDone && currentPhase === 'ready') {
        smokeDone = true;
        log('[smoke] 页面加载成功');
        console.log('SMOKE_OK');
        setTimeout(() => app.quit(), 1500);
      }
      if (SHOT && !shotDone) {
        shotDone = true;
        setTimeout(captureShot, 4000); // 等 React 渲染稳定再截
      }
    }
  });

  showBoot('starting', '正在启动 DSH 桌面版…');
}

// 界面打磨：把整个页面（body）整体下移 TITLEBAR_H 高度，让出顶部「标题栏带」。
// 关键点：transform 作用于 body 而非 #root —— body 的 transform 会建立新的
// 包含块，使 body 内【所有】fixed 元素（含 createPortal 到 body 的 Modal /
// 菜单 / Popover 浮层）都统一下移，不会漏掉浮层导致与右上角按钮重叠。
// 顶部条带可拖拽移动窗口（top 用负值抵消 body 位移）。
function polishTargetPage() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const js = `(() => {
    const BAR_H = ${TITLEBAR_H};
    const apply = () => {
      const b = document.body;
      if (!b) return false;
      b.style.transform = 'translateY(' + BAR_H + 'px)';
      b.style.height = 'calc(100% - ' + BAR_H + 'px)';
      b.style.minHeight = 'calc(100% - ' + BAR_H + 'px)';
      let strip = document.getElementById('dshDesktopDrag');
      if (!strip) {
        strip = document.createElement('div');
        strip.id = 'dshDesktopDrag';
        // z-index 用中间值（高于静态内容、低于页面浮层面板 100+）：
        // 命中测试只把事件交给最上层元素——空白带命中条带拖窗口，
        // 面板/浮层覆盖的区域命中面板，互不冲突（勿改回最高层）
        strip.style.cssText =
          'position:fixed;top:-' + BAR_H + 'px;left:0;right:0;height:' + BAR_H + 'px;' +
          'z-index:10;-webkit-app-region:drag;';
        document.body.appendChild(strip);
      }
      return true;
    };
    if (apply()) return true;
    let n = 0;
    const t = setInterval(() => { if (apply() || ++n > 20) clearInterval(t); }, 500);
    return true;
  })()`;
  mainWindow.webContents.executeJavaScript(js).catch(() => {});
}

// 截图调试模式：自检 body 位移、portal 浮层是否同步下移、有无裁切，再存 PNG 后退出
function captureShot() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const inspectJs = `(() => {
    const BAR_H = ${TITLEBAR_H};
    const br = document.body.getBoundingClientRect();
    const strip = document.getElementById('dshDesktopDrag');
    const sr = strip ? strip.getBoundingClientRect() : null;
    // 探针：body 级 fixed 元素（portal 同机制）应随 body 下移 BAR_H
    let probeTop = null;
    const probe = document.createElement('div');
    probe.style.cssText = 'position:fixed;top:0;left:0;width:10px;height:10px;pointer-events:none;';
    document.body.appendChild(probe);
    probeTop = Math.round(probe.getBoundingClientRect().top);
    probe.remove();
    return JSON.stringify({
      winW: window.innerWidth,
      winH: window.innerHeight,
      bodyTop: Math.round(br.top),
      bodyBottom: Math.round(br.bottom),
      bodyFits: (Math.abs(br.top - BAR_H) <= 2 && br.bottom <= window.innerHeight + 2),
      stripFound: !!strip,
      stripTop: sr ? Math.round(sr.top) : null,
      stripH: sr ? Math.round(sr.height) : null,
      probeTop,
      probeShifted: probeTop === BAR_H,
      noScroll: document.documentElement.scrollHeight <= window.innerHeight + 1
    });
  })()`;
  mainWindow.webContents.executeJavaScript(inspectJs).then((s) => {
    log('[shot] inspect ' + s);
    console.log('SHOT_INSPECT ' + s);
    return mainWindow.webContents.capturePage();
  }).then((img) => {
    const file = path.join(logDir, `shot-${Date.now()}.png`);
    fs.writeFileSync(file, img.toPNG());
    log('[shot] 已保存 ' + file);
    console.log('SHOT_SAVED ' + file);
    setTimeout(() => app.quit(), 500);
  }).catch((e) => {
    log('[shot] 截图失败 ' + e.message);
    app.quit();
  });
}

function showBoot(phase, message) {
  currentPhase = phase;
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.loadFile(path.join(__dirname, 'boot.html'));
  sendStatus(phase, message, tailLog(20));
}

// ---------- IPC（boot 页按钮 → 主进程） ----------
ipcMain.handle('dsh-desktop:status', () => lastStatus);
ipcMain.handle('dsh-desktop:restart', () => {
  log('用户点击重新启动');
  killAllChildren(); // 清掉 DSH 与（若有）残留的安装进程
  showBoot('starting', '正在重新启动 DSH…');
  startup();
});
ipcMain.handle('dsh-desktop:quit', () => app.quit());

// ---------- 应用生命周期 ----------
// 单实例锁：同一 userData（%APPDATA%/dsh-desktop，dev 与打包版共用）只允许一个实例。
// SMOKE/SHOT 为自动化测试模式，跳过锁，避免与正在运行的实例互斥。
const gotLock = SMOKE || SHOT ? true : app.requestSingleInstanceLock();
if (!gotLock) {
  log('检测到 DSH 桌面版已在运行，本实例退出（单实例锁）');
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(() => {
    nativeTheme.themeSource = 'dark'; // 原生对话框/菜单跟随深色
    if (INSTALL_SHORTCUT) { makeShortcut(); return; } // 工具模式：建完即退
    createWindow();
    startup();
  });

  // 关窗即退出；退出前把后台进程（DSH / npm 安装）一起带走（需求 2）
  app.on('window-all-closed', () => app.quit());
  app.on('before-quit', () => {
    quitting = true;
    killAllChildren();
  });
  process.on('exit', () => {
    killAllChildren();
  });
}
