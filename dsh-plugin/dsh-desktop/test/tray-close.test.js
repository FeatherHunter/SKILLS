'use strict';

// 托盘生命周期自动化验证（Windows）：
//   A. 正常启动 → 关窗（CDP 模拟点 ✕）→ 隐藏到托盘：桌面壳与假 DSH 均存活
//   B. 隐藏启动（DSH_DESKTOP_HIDDEN=1）→ 窗口不显示、托盘常驻、DSH 正常运行；关窗仍存活
// 用法：node test/tray-close.test.js   （需先 npm install 过 electron；不触碰真实 DSH/数据库）

const { spawn, execSync } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

if (typeof WebSocket === 'undefined') {
  console.error('需要 Node >= 22（原生 WebSocket，CDP 驱动用）');
  process.exit(2);
}

const ROOT = path.join(__dirname, '..');
const ELECTRON = path.join(ROOT, 'node_modules', 'electron', 'dist', 'electron.exe');
const LOG = path.join(process.env.APPDATA, 'dsh-desktop', 'dsh.log');
const TEST_UD_ROOT = path.join(process.env.TEMP || '.', 'dsh-desktop-test-ud'); // 独立 userData：绕过单实例锁，不影响用户真实实例
const CDP_PORT = 9333;
const FAKE_A = 3099;
const FAKE_B = 3100;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const assert = (cond, msg) => { if (!cond) throw new Error('断言失败: ' + msg); };

function httpGet(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let b = '';
      res.on('data', (d) => { b += d; });
      res.on('end', () => resolve(b));
    }).on('error', reject);
  });
}

function logCharLen() {
  try { return fs.readFileSync(LOG, 'utf8').length; } catch { return 0; }
}

// 注意：日志含中文多字节字符，偏移必须按「字符数」记录与切片，不能用文件字节数
function logTail(from) {
  try { return fs.readFileSync(LOG, 'utf8').slice(from); } catch { return ''; }
}

async function waitFor(fn, timeoutMs, label) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const v = await fn();
    if (v) return v;
    await sleep(300);
  }
  throw new Error('超时等待: ' + label);
}

async function startFakeServer(port) {
  const proc = spawn(process.execPath, [path.join(__dirname, 'smoke-server.js')], {
    env: { ...process.env, DSH_DESKTOP_PORT: String(port) },
    stdio: 'ignore',
  });
  await waitFor(async () => {
    try { return (await httpGet('http://127.0.0.1:' + port + '/')).includes('__DSH_BOOT__'); }
    catch { return false; }
  }, 10000, '假 DSH 就绪 on ' + port);
  return proc;
}

function launchApp(env, extraArgs) {
  return spawn(ELECTRON, ['.', '--remote-debugging-port=' + CDP_PORT].concat(extraArgs || []), {
    cwd: ROOT,
    env: { ...process.env, ...env },
    stdio: 'ignore',
  });
}

function assertAlive(pid, label) {
  try { process.kill(pid, 0); return true; }
  catch { throw new Error('进程已退出: ' + label); }
}

function killTree(proc) {
  if (!proc || !proc.pid) return;
  try { execSync('taskkill /pid ' + proc.pid + ' /T /F', { stdio: 'ignore' }); } catch { /* 已退出 */ }
}

async function cdpEvaluate(wsUrl, expression) {
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('CDP WebSocket 连接失败')); });
  const msg = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('CDP evaluate 超时')), 10000);
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id === 1) { clearTimeout(timer); resolve(m); }
    };
    ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression, awaitPromise: true } }));
  });
  ws.close();
  if (msg.error) throw new Error('CDP 错误: ' + JSON.stringify(msg.error));
  return msg.result;
}

async function findPageTarget(urlPart) {
  const list = await (await fetch('http://127.0.0.1:' + CDP_PORT + '/json/list')).json();
  return list.find((t) => t.type === 'page' && t.url.includes(urlPart)) || null;
}

async function closeViaCDP(urlPart) {
  const page = await waitFor(() => findPageTarget(urlPart), 10000, 'CDP 页面目标 ' + urlPart);
  await cdpEvaluate(page.webSocketDebuggerUrl, 'window.dshDesktop.close()');
}

// ---------- 流程 A：关窗 → 隐藏到托盘 ----------
async function flowA() {
  const server = await startFakeServer(FAKE_A);
  const logStart = logCharLen();
  const app = launchApp({ DSH_DESKTOP_PORT: String(FAKE_A), DSH_DESKTOP_USER_DATA: path.join(TEST_UD_ROOT, 'a') });
  try {
    // 端口上已有假 DSH → app 走「连接现有实例」分支（日志为「已有 DSH 实例」），不会出现「DSH 就绪」
    const readyA = (tail) => tail.includes('已有 DSH 实例') || tail.includes('DSH 就绪');
    const tail0 = await waitFor(() => { const t = logTail(logStart); return readyA(t) ? t : null; }, 30000, '流程A: 连接就绪');
    assert(!tail0.includes('已在运行'), '流程A: 不应命中单实例锁（前一个实例未清理？）');
    await waitFor(() => logTail(logStart).includes('托盘已创建'), 10000, '流程A: 托盘已创建');

    await closeViaCDP('127.0.0.1:' + FAKE_A);
    await waitFor(() => logTail(logStart).includes('窗口关闭 → 隐藏到托盘'), 8000, '流程A: 隐藏到托盘日志');

    assertAlive(app.pid, '流程A: 桌面壳');
    const body = await httpGet('http://127.0.0.1:' + FAKE_A + '/');
    assert(body.includes('__DSH_BOOT__'), '流程A: 关窗后假 DSH 仍在服务');
    console.log('FLOW_A_PASS: 关窗 → 隐藏到托盘，桌面壳与 DSH 均存活');
  } finally {
    killTree(app);
    killTree(server);
  }
}

// ---------- 流程 B：隐藏启动（服务化） ----------
async function flowB() {
  const server = await startFakeServer(FAKE_B);
  const logStart = logCharLen();
  const app = launchApp({ DSH_DESKTOP_PORT: String(FAKE_B), DSH_DESKTOP_HIDDEN: '1', DSH_DESKTOP_USER_DATA: path.join(TEST_UD_ROOT, 'b') });
  try {
    await waitFor(() => logTail(logStart).includes('隐藏启动模式'), 20000, '流程B: 隐藏启动日志');
    await waitFor(() => logTail(logStart).includes('托盘已创建'), 10000, '流程B: 托盘已创建');
    const readyB = (tail) => tail.includes('已有 DSH 实例') || tail.includes('DSH 就绪');
    await waitFor(() => readyB(logTail(logStart)), 30000, '流程B: 连接就绪');

    assertAlive(app.pid, '流程B: 桌面壳');
    const body = await httpGet('http://127.0.0.1:' + FAKE_B + '/');
    assert(body.includes('__DSH_BOOT__'), '流程B: 隐藏模式下 DSH 正常运行');

    // 隐藏窗口再触发 close → 仍隐藏、仍存活
    await closeViaCDP('127.0.0.1:' + FAKE_B);
    await waitFor(() => logTail(logStart).includes('窗口关闭 → 隐藏到托盘'), 8000, '流程B: 隐藏中关窗日志');
    assertAlive(app.pid, '流程B: 关窗后桌面壳');
    console.log('FLOW_B_PASS: 隐藏启动 → 托盘常驻，DSH 正常运行，关窗仍存活');
  } finally {
    killTree(app);
    killTree(server);
  }
}

(async () => {
  try {
    await flowA();
    await flowB();
    console.log('ALL_TRAY_TESTS_PASS');
    process.exit(0);
  } catch (e) {
    console.error('TEST_FAIL: ' + e.message);
    process.exit(1);
  }
})();
