'use strict';

// 检查更新全链路集成测试（不碰真实网络/registry）：
//   本地假 registry（/latest → 指定版本）+ 假 DSH（__DSH_BOOT__）+ 桌面壳（隔离 userData）
//   CDP 调 window.dshDesktop.checkUpdate() 验证判定，并验证标题栏注入按钮的静默检查渲染。
// 场景：A 按钮渲染（registry 先就绪 → 加载后静默检查成功 → 显示「升级至 9.9.9」）
//       B 有新版判定 / C 无新版判定 / D registry 不可达优雅失败
// 用法：node test/update-flow.test.js

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
const CDP_PORT = 9334;
const FAKE_DSH_PORT = 3091;
const FAKE_REG_PORT = 3900;
const TEST_UD = path.join(process.env.TEMP || '.', 'dsh-desktop-test-update-ud');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const assert = (cond, msg) => { if (!cond) throw new Error('断言失败: ' + msg); };

function httpGet(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let b = '';
      res.on('data', (d) => { b += d; });
      res.on('end', () => resolve({ status: res.statusCode, body: b }));
    }).on('error', reject);
  });
}
function logCharLen() { try { return fs.readFileSync(LOG, 'utf8').length; } catch { return 0; } }
function logTail(from) { try { return fs.readFileSync(LOG, 'utf8').slice(from); } catch { return ''; } }
async function waitFor(fn, timeoutMs, label) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const v = await fn();
    if (v) return v;
    await sleep(300);
  }
  throw new Error('超时等待: ' + label);
}
function killTree(proc) {
  if (!proc || !proc.pid) return;
  try { execSync('taskkill /pid ' + proc.pid + ' /T /F', { stdio: 'ignore' }); } catch { /* 已退出 */ }
}

function startFakeRegistry(latestVersion) {
  const server = http.createServer((req, res) => {
    if (req.url === '/@deepseek-ai/dsh/latest') {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ name: '@deepseek-ai/dsh', version: latestVersion }));
    } else { res.writeHead(404); res.end(); }
  });
  return new Promise((resolve) => { server.listen(FAKE_REG_PORT, '127.0.0.1', () => resolve(server)); });
}

async function startFakeDsh() {
  const proc = spawn(process.execPath, [path.join(__dirname, 'smoke-server.js')], {
    env: { ...process.env, DSH_DESKTOP_PORT: String(FAKE_DSH_PORT) },
    stdio: 'ignore',
  });
  await waitFor(async () => {
    try { return (await httpGet('http://127.0.0.1:' + FAKE_DSH_PORT + '/')).body.includes('__DSH_BOOT__'); }
    catch { return false; }
  }, 10000, '假 DSH 就绪');
  return proc;
}

async function cdpEvaluate(wsUrl, expression) {
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('CDP 连接失败')); });
  const msg = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('CDP 超时')), 15000);
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id === 1) { clearTimeout(timer); resolve(m); }
    };
    ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression, awaitPromise: true, returnByValue: true } }));
  });
  ws.close();
  if (msg.error) throw new Error('CDP 错误: ' + JSON.stringify(msg.error));
  if (msg.result.exceptionDetails) throw new Error('页面执行异常: ' + JSON.stringify(msg.result.exceptionDetails));
  return msg.result.result.value;
}

async function main() {
  const results = [];
  let reg = await startFakeRegistry('9.9.9'); // 先就绪：页面加载时的静默检查要成功
  const dsh = await startFakeDsh();
  const log0 = logCharLen();
  const app = spawn(ELECTRON, ['.', '--remote-debugging-port=' + CDP_PORT], {
    cwd: ROOT,
    env: {
      ...process.env,
      DSH_DESKTOP_PORT: String(FAKE_DSH_PORT),
      DSH_DESKTOP_REGISTRY: 'http://127.0.0.1:' + FAKE_REG_PORT,
      DSH_DESKTOP_USER_DATA: TEST_UD,
    },
    stdio: 'ignore',
  });
  try {
    await waitFor(() => logTail(log0).includes('已有 DSH 实例') || logTail(log0).includes('DSH 就绪'), 30000, '连接假 DSH');
    const page = await waitFor(async () => {
      const list = await (await fetch('http://127.0.0.1:' + CDP_PORT + '/json/list')).json();
      return list.find((t) => t.type === 'page' && t.url.includes('127.0.0.1:' + FAKE_DSH_PORT)) || null;
    }, 10000, 'CDP 页面目标');
    const ws = page.webSocketDebuggerUrl;

    // 场景 A：注入按钮存在且静默检查后显示「升级至 9.9.9」
    const btnState = await waitFor(async () => {
      const s = await cdpEvaluate(ws, `(() => {
        const b = document.getElementById('dshdUpdateBtn');
        if (!b) return 'NO_BUTTON';
        if (b.textContent === '检查中…') return 'CHECKING';
        return JSON.stringify({ text: b.textContent, color: b.style.color, disabled: b.disabled });
      })()`);
      if (s === 'CHECKING' || s === 'NO_BUTTON') return null;
      return s;
    }, 15000, '按钮渲染稳定');
    const bs = JSON.parse(btnState);
    assert(bs.text === '升级至 9.9.9', '按钮应显示升级提示，实际: ' + btnState);
    results.push('场景A PASS: 注入按钮静默检查 → 「' + bs.text + '」（绿 ' + bs.color + '）');

    // 场景 B：checkUpdate 判定有新版
    const rB = await cdpEvaluate(ws, 'window.dshDesktop.checkUpdate()');
    assert(rB && rB.ok === true, 'B ok: ' + JSON.stringify(rB));
    assert(rB.hasUpdate === true && rB.latest === '9.9.9', 'B 应有更新: ' + JSON.stringify(rB));
    assert(typeof rB.current === 'string' && rB.current.length > 0, 'B current 缺失: ' + JSON.stringify(rB));
    results.push('场景B PASS: 有新版判定（' + rB.current + ' → 9.9.9）');

    // 场景 C：无新版（registry 换成 0.0.1）
    reg.close();
    reg = await startFakeRegistry('0.0.1');
    const rC = await cdpEvaluate(ws, 'window.dshDesktop.checkUpdate()');
    assert(rC && rC.ok === true && rC.hasUpdate === false, 'C 不应有更新: ' + JSON.stringify(rC));
    results.push('场景C PASS: 无新版判定（latest=0.0.1）');

    // 场景 D：registry 不可达 → 优雅失败
    reg.close();
    await sleep(300);
    const rD = await cdpEvaluate(ws, 'window.dshDesktop.checkUpdate()');
    assert(rD && rD.ok === false && rD.error, 'D 应 ok=false 带错误: ' + JSON.stringify(rD));
    results.push('场景D PASS: registry 不可达 → 优雅失败（error=' + rD.error + '）');
  } finally {
    try { reg.close(); } catch { /* 已关 */ }
    killTree(app);
    killTree(dsh);
  }
  results.forEach((r) => console.log(r));
  console.log('ALL_UPDATE_FLOW_TESTS_PASS');
  process.exit(0);
}

main().catch((e) => { console.error('TEST_FAIL: ' + e.message); process.exit(1); });
