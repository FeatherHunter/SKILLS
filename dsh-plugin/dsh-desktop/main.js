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
const https = require('https');
const net = require('net');
const path = require('path');
const fs = require('fs');

// ---------- 配置 ----------
const DEFAULT_PORT = 3080;
const START_TIMEOUT_MS = 10 * 60 * 1000; // 首次安装/启动 DSH 包（数百 MB），放宽到 10 分钟
const POLL_INTERVAL_MS = 600;
const TITLEBAR_H = 40; // 顶部标题栏带高度：页面内容下移量 = WCO 按钮悬浮区高度

// 安装镜像候选：官方源 + 国内镜像（首次安装自动测速选快，避免「下载很久像卡死」）
const REGISTRIES = [
  { name: '官方源', url: 'https://registry.npmjs.org' },
  { name: '国内镜像 npmmirror', url: 'https://registry.npmmirror.com' },
];
const PING_TIMEOUT_MS = 5000;       // 每个源的测速超时
const PROGRESS_INTERVAL_MS = 1500;  // 安装进度轮询间隔
const STALL_SECONDS = 90;           // 连续多久无字节增长判定「下载停滞」，提示用户可换镜像
const ESTIMATED_DOWNLOAD_MB = 600;  // 进度条估算总量（DSH 全依赖树约几百 MB，仅用于百分比显示）

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
let copyStartTs = 0;     // 复用复制开始时间戳（进度显示用）
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

// ---------- 安装辅助：测速 / 进度 / 复用检测 ----------

// 探测一个 npm 镜像源的可达性与延迟（返回 ms；不可达返回 -1）
function pingRegistry(url) {
  return new Promise((resolve) => {
    const start = Date.now();
    const mod = url.startsWith('https:') ? require('https') : http;
    const req = mod.get(url + '/-/ping', { timeout: PING_TIMEOUT_MS }, (res) => {
      res.resume();
      resolve(res.statusCode >= 200 && res.statusCode < 500 ? Date.now() - start : -1);
    });
    req.on('timeout', () => { req.destroy(); resolve(-1); });
    req.on('error', () => resolve(-1));
  });
}

// 挑选安装源：环境变量指定 > 并发测速选快 > 默认官方源
async function pickRegistry() {
  const forced = process.env.DSH_DESKTOP_REGISTRY;
  if (forced) return { name: '环境变量指定', url: forced };
  const results = await Promise.all(REGISTRIES.map(async (r) => ({ ...r, ms: await pingRegistry(r.url) })));
  const reachable = results.filter((r) => r.ms >= 0);
  if (reachable.length === 0) {
    log('runtime: 所有源测速均不可达，退回官方源');
    return REGISTRIES[0];
  }
  reachable.sort((a, b) => a.ms - b.ms);
  log('runtime: 测速 ' + reachable.map((r) => `${r.name}=${r.ms}ms`).join('，') + ' → 选用 ' + reachable[0].name);
  return reachable[0];
}

// 真实进度：统计 runtime 下已落地的包数（node_modules 顶层 + @scope 子包）与总字节数
function runtimeProgress() {
  let packages = 0, bytes = 0;
  const nm = path.join(RUNTIME_DIR, 'node_modules');
  try {
    for (const e of fs.readdirSync(nm, { withFileTypes: true })) {
      const p = path.join(nm, e.name);
      if (e.isDirectory()) {
        if (e.name.startsWith('@')) {
          let sub = 0;
          for (const s of fs.readdirSync(p, { withFileTypes: true })) if (s.isDirectory()) sub++;
          packages += Math.max(sub, 1);
        } else packages += 1;
        bytes += dirSize(p);
      } else if (e.name === '.package-lock.json') {
        try { bytes += fs.statSync(p).size; } catch { /* 忽略 */ }
      }
    }
  } catch { /* 安装中目录可能还不存在 */ }
  return { packages, bytes };
}

function dirSize(dir) {
  let total = 0;
  try {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) total += dirSize(p);
      else {
        try { total += fs.statSync(p).size; } catch { /* 忽略 */ }
      }
    }
  } catch { /* 忽略 */ }
  return total;
}

// 复用检测：本机 npm 缓存（_npx）里已有 DSH 就直接复制，跳过联网下载（老用户/开发者秒开）
function tryReuseNpxCache() {
  const npxRoot = process.env.LOCALAPPDATA
    ? path.join(process.env.LOCALAPPDATA, 'npm-cache', '_npx')
    : null;
  if (!npxRoot || !fs.existsSync(npxRoot)) return null;
  try {
    for (const entry of fs.readdirSync(npxRoot, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const cand = path.join(npxRoot, entry.name, 'node_modules', '@deepseek-ai', 'dsh', 'lib', 'bin.js');
      if (fs.existsSync(cand)) return path.join(npxRoot, entry.name, 'node_modules');
    }
  } catch { /* 忽略 */ }
  return null;
}

// 异步复制目录（分片 + setImmediate 让出事件循环，主进程不阻塞、UI 能持续刷新进度）
function copyDirAsync(src, dst, onProgress) {
  return new Promise((resolve, reject) => {
    const items = [];
    const walk = (dir) => {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const s = path.join(dir, e.name);
        const d = path.join(dst, path.relative(src, s));
        if (e.isDirectory()) { items.push({ s, d, dir: true }); walk(s); }
        else items.push({ s, d, dir: false });
      }
    };
    try { walk(src); } catch (err) { reject(err); return; }
    const total = items.length;
    let done = 0;
    const queue = items.slice();
    const step = () => {
      try {
        const batch = queue.splice(0, 200);
        for (const it of batch) {
          if (it.dir) fs.mkdirSync(it.d, { recursive: true });
          else {
            fs.mkdirSync(path.dirname(it.d), { recursive: true });
            fs.copyFileSync(it.s, it.d);
          }
          done++;
        }
        onProgress(done, total);
        if (queue.length > 0) setImmediate(step);
        else resolve();
      } catch (err) { reject(err); }
    };
    step();
  });
}

// 确保 DSH 运行时已安装（内置 npm 自动安装，首次联网下载，之后离线可用）
// 顺序：已有 DSH_BIN → 直接可用；本机 npx 缓存有 DSH → 复制复用（免联网）；
//      否则 npm install（自动测速选源 + 真实进度 + 停滞检测）。
function ensureRuntime(onDone, opts = {}) {
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

  // ① 复用检测：npx 缓存有现成 DSH → 直接复制（秒级，免几百 MB 下载）
  if (!opts.skipReuse && process.env.DSH_DESKTOP_REINSTALL !== '1') {
    const src = tryReuseNpxCache();
    if (src) {
      log('runtime: 发现 npm 缓存中的 DSH，复制复用（免联网下载）← ' + src);
      sendStatus('installing', '发现本机已有 DSH，正在复制（免联网下载）…', tailLog(4));
      runtimeBusy = true;
      copyStartTs = Date.now();
      const dst = path.join(RUNTIME_DIR, 'node_modules');
      copyDirAsync(src, dst, (done, total) => {
        const secs = Math.round((Date.now() - copyStartTs) / 1000);
        const { packages, bytes } = runtimeProgress();
        sendStatus('installing',
          `正在复制本机已有的 DSH（${done}/${total} 项，已 ${secs}s）…\n比联网下载快得多，马上就好。`,
          tailLog(4), { progress: { packages, bytes, secs, total, done } });
      }).then(() => {
        runtimeBusy = false;
        log('runtime: 复用复制完成，DSH_BIN=' + DSH_BIN + ' exists=' + fs.existsSync(DSH_BIN));
        onDone(fs.existsSync(DSH_BIN));
      }).catch((err) => {
        runtimeBusy = false;
        log('runtime: 复用复制失败（' + err.message + '），回退联网安装');
        ensureRuntime(onDone, { ...opts, skipReuse: true });
      });
      return;
    }
  }

  // ② 联网安装：先测速选源，再 npm install（真实进度 + 停滞检测）
  const doInstall = (registry) => {
    const installStartedAt = Date.now();
    log('runtime: 开始安装 DSH（npm install @deepseek-ai/dsh → ' + RUNTIME_DIR + '，源=' + registry.name + '）');
    sendStatus('installing',
      `首次使用：正在下载并安装 DSH 运行时…\n当前源：${registry.name}（自动测速选择，装好后即可离线使用）`,
      tailLog(4));
    runtimeBusy = true;
    installProc = spawn(process.execPath, [
      NPM_CLI, 'install', '--prefix', RUNTIME_DIR, '--no-audit', '--no-fund',
      '--loglevel', 'error', '--registry', registry.url, '@deepseek-ai/dsh',
    ], {
      windowsHide: true,
      detached: process.platform !== 'win32',
      stdio: ['ignore', 'pipe', 'pipe'],
      env: NODE_ENV,
    });
    installProc.stdout.on('data', (d) => log('[npm] ' + String(d).trim()));
    installProc.stderr.on('data', (d) => log('[npm] ' + String(d).trim()));
    let lastBytes = -1;
    let stallSince = null;
    let stalled = false;
    const progress = setInterval(() => {
      const { packages, bytes } = runtimeProgress();
      const secs = Math.round((Date.now() - installStartedAt) / 1000);
      // 停滞检测：字节数长时间不增长 → 提示换镜像
      if (bytes === lastBytes) {
        if (stallSince === null) stallSince = Date.now();
        else if (!stalled && Date.now() - stallSince > STALL_SECONDS * 1000) {
          stalled = true;
          log('runtime: 检测到下载停滞 ' + STALL_SECONDS + 's（源 ' + registry.name + '），提示用户换镜像');
          sendStatus('installing',
            `下载似乎停滞了 ${STALL_SECONDS}s（可能是网络原因）。\n可以点下方「切换镜像重试」，或再等等看。`,
            tailLog(4), { stalled: true, registry: registry.name });
          return;
        }
      } else { stallSince = null; stalled = false; }
      lastBytes = bytes;
      const pct = Math.min(100, Math.round(bytes / 1048576 / ESTIMATED_DOWNLOAD_MB * 100));
      sendStatus('installing',
        `正在下载并安装 DSH 运行时…（已进行 ${secs}s，首次大包下载需要几分钟）\n当前源：${registry.name} · 已下载约 ${(bytes / 1048576).toFixed(0)} MB（${packages} 个包，约 ${pct}%）`,
        tailLog(4), { progress: { packages, bytes, secs }, registry: registry.name });
    }, PROGRESS_INTERVAL_MS);
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
  };

  const run = async () => {
    let registry;
    try {
      registry = opts.registry || (await pickRegistry());
    } catch (err) {
      log('runtime: 测速失败，退回官方源：' + err.message);
      registry = REGISTRIES[0];
    }
    doInstall(registry);
  };
  run();
}

// ---------- 启动流程 ----------
// 拉起 DSH 服务并等待就绪（startup 与「切换镜像重试」共用）
function launchDsh() {
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
}

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
      const launch = () => launchDsh();
      if (customCommand()) {
        launch(); // 高级模式：用户自定义命令（无需内置运行时）
      } else {
        ensureRuntime((ok) => {
          if (!ok) {
            onChildGone('DSH 运行时安装失败。\n请检查网络后点「重新启动」重试；\n或点下方「切换镜像重试」换国内镜像；\n也可以设环境变量 DSH_DESKTOP_REGISTRY 指定可用源。');
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
    // frame:false —— 整个窗口都是客户区，顶部所有鼠标事件都进页面。
    // 之前用 titleBarStyle hidden + WCO：顶部 40px 是系统非客户区（标题栏），
    // 页面永远收不到那里的点击，插件面板拖到顶部后会被系统吞掉事件。
    // 窗口控制按钮（最小化/最大化/关闭）改为页面自绘（见 polishTargetPage / boot.html）。
    winOpts.frame = false;
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
// 窗口移动用「手动拖拽」：不用 -webkit-app-region（它会在合成器层截胡
// 事件，导致顶部区域的面板手柄永远抢不到鼠标）。事件走正常 DOM 通道，
// 按 mousedown 的目标元素区分：空白带（条带/body）拖窗口，
// 面板/浮层命中时是面板元素 → 面板自己的拖拽，互不冲突。
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
        // 普通元素（无 -webkit-app-region）：事件走 DOM 命中测试。
        // z-index 中间值：空白带命中条带，浮层面板（z-index 100+）覆盖区命中面板。
        strip.style.cssText =
          'position:fixed;top:-' + BAR_H + 'px;left:0;right:0;height:' + BAR_H + 'px;' +
          'z-index:10;';
        document.body.appendChild(strip);
      }
      return true;
    };
    const installDrag = () => {
      if (window.__dshDesktopDragInstalled) return;
      window.__dshDesktopDragInstalled = true;
      const api = window.dshDesktop;

      // 自绘窗口控制按钮（frame:false 后系统按钮不存在）
      let wc = document.getElementById('dshdWinControls');
      if (!wc) {
        wc = document.createElement('div');
        wc.id = 'dshdWinControls';
        wc.style.cssText = 'position:fixed;top:-' + BAR_H + 'px;right:0;height:40px;display:flex;align-items:center;z-index:2147483647;';
        const mkBtn = (glyph, onClick, hoverBg) => {
          const b = document.createElement('button');
          b.textContent = glyph;
          b.style.cssText = 'width:46px;height:40px;border:0;background:0 0;color:#a1a1aa;' +
            'font-size:12px;font-family:system-ui,sans-serif;cursor:pointer;display:grid;place-items:center;padding:0;';
          b.addEventListener('mouseenter', () => { b.style.background = hoverBg; });
          b.addEventListener('mouseleave', () => { b.style.background = '0 0'; });
          b.addEventListener('click', onClick);
          return b;
        };
        wc.appendChild(mkBtn('─', () => api.minimize(), 'rgba(255,255,255,0.08)'));
        wc.appendChild(mkBtn('□', () => api.toggleMaximize(), 'rgba(255,255,255,0.08)'));
        const closeBtn = mkBtn('✕', () => api.close(), 'rgba(232,17,35,0.85)');
        closeBtn.style.color = '#d4d4d4';
        closeBtn.addEventListener('mouseenter', () => { closeBtn.style.color = '#ffffff'; });
        closeBtn.addEventListener('mouseleave', () => { closeBtn.style.color = '#d4d4d4'; });
        wc.appendChild(closeBtn);
        document.body.appendChild(wc);
      }

      const strip = document.getElementById('dshDesktopDrag');
      // 空白带判定：命中条带本身 / body / 根容器。
      // 页面内容已下移，0-40px 内除浮层面板外无其他元素；
      // 面板命中时 target 是面板元素 → 不拖窗口，面板自己处理。
      const isBlank = (el) => el === strip || el === document.body || el.id === 'root';
      let drag = null;
      document.addEventListener('mousedown', (e) => {
        if (e.button !== 0 || e.clientY >= BAR_H || !isBlank(e.target)) return;
        drag = { sx: e.screenX, sy: e.screenY, moved: false };
        e.preventDefault();
        api.dragStart();
      });
      document.addEventListener('mousemove', (e) => {
        if (!drag) return;
        const dx = e.screenX - drag.sx;
        const dy = e.screenY - drag.sy;
        if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 3) return; // 防误触阈值
        drag.moved = true;
        api.dragMove(dx, dy);
      });
      const endDrag = () => {
        if (drag) { drag = null; api.dragEnd(); }
      };
      document.addEventListener('mouseup', endDrag);
      window.addEventListener('blur', endDrag); // 鼠标拖出窗口时兜底
      document.addEventListener('dblclick', (e) => {
        if (e.clientY < BAR_H && isBlank(e.target)) api.toggleMaximize();
      });
    };
    if (apply()) { installDrag(); return true; }
    let n = 0;
    const t = setInterval(() => {
      if (apply()) { clearInterval(t); installDrag(); }
      else if (++n > 20) clearInterval(t);
    }, 500);
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
ipcMain.handle('dsh-desktop:retry-install', () => {
  log('用户点击「切换镜像重试」');
  // 停掉当前安装进程，用国内镜像（npmmirror）重装；用户也可通过 DSH_DESKTOP_REGISTRY 指定其它源
  const mirror = REGISTRIES.find((r) => /npmmirror/i.test(r.url)) || REGISTRIES[1] || REGISTRIES[0];
  if (installProc) {
    try { killTree(installProc); } catch { /* 忽略 */ }
    installProc = null;
  }
  runtimeBusy = false;
  sendStatus('installing', `正在用「${mirror.name}」重新安装 DSH 运行时…`, tailLog(4));
  ensureRuntime((ok) => {
    if (!ok) {
      onChildGone('镜像重装仍失败。\n请检查网络，或设置环境变量 DSH_DESKTOP_REGISTRY 指定可用源后点「重新启动」。');
      return;
    }
    launchDsh();
  }, { registry: mirror, skipReuse: true });
});
ipcMain.handle('dsh-desktop:quit', () => app.quit());

// ---------- IPC（手动窗口拖拽，页面注入 → 主进程） ----------
// 手动拖拽替代 -webkit-app-region：事件走 DOM 通道，与页面浮层零冲突。
let dragOrigin = null; // 拖拽起点的窗口位置
ipcMain.on('dsh-desktop:drag-start', () => {
  const win = mainWindow;
  if (!win || win.isDestroyed()) return;
  const [x, y] = win.getPosition();
  dragOrigin = { x, y };
});
ipcMain.on('dsh-desktop:drag-move', (_e, dx, dy) => {
  const win = mainWindow;
  if (!win || win.isDestroyed() || !dragOrigin) return;
  win.setPosition(Math.round(dragOrigin.x + dx), Math.round(dragOrigin.y + dy));
});
ipcMain.on('dsh-desktop:drag-end', () => { dragOrigin = null; });
ipcMain.handle('dsh-desktop:toggle-maximize', () => {
  const win = mainWindow;
  if (!win || win.isDestroyed()) return;
  if (win.isMaximized()) win.unmaximize(); else win.maximize();
});
ipcMain.handle('dsh-desktop:minimize', () => {
  const win = mainWindow;
  if (win && !win.isDestroyed()) win.minimize();
});
ipcMain.handle('dsh-desktop:close', () => {
  app.quit();
});

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
