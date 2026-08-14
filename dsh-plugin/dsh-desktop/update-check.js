'use strict';

// ============================================================
// DSH 升级检测 · 纯逻辑模块（零依赖，可单测）
//
// 职责：
//   1. semver 2.0.0 版本比较（含 prerelease，如 0.1.0-rc.6 vs 0.1.0-rc.10）
//   2. 查 npm registry 的 @deepseek-ai/dsh latest 版本（可注入 fetcher 便于测试）
//   3. 组装「当前版本 vs 最新版本」判定结果
//
// 为什么自写比较器：主进程零依赖设计；npm 捆绑的 semver 在打包后路径依赖
// afterPack 修复（存在但脆弱），自写 ~50 行 + 测试语料对拍即可覆盖。
// ============================================================

const https = require('https');
const http = require('http');

// ---------- semver 解析与比较（semver 2.0.0） ----------

// '0.1.0-rc.6+build' → { major, minor, patch, prerelease: ['rc','6'], build }
function parseVersion(v) {
  if (typeof v !== 'string') return null;
  const m = /^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$/.exec(v.trim());
  if (!m) return null;
  return {
    major: Number(m[1]), minor: Number(m[2]), patch: Number(m[3]),
    prerelease: m[4] ? m[4].split('.') : null,
    build: m[5] || null,
  };
}

// 单个 prerelease 标识符比较：数字按数值（rc.10 > rc.6），数字 < 字母，字母按 ASCII
function cmpId(a, b) {
  const an = /^\d+$/.test(a);
  const bn = /^\d+$/.test(b);
  if (an && bn) return Number(a) - Number(b) || 0;
  if (an) return -1;
  if (bn) return 1;
  return a < b ? -1 : a > b ? 1 : 0;
}

// 返回负/零/正；任一解析失败返回 NaN（调用方须先判断）
function compareVersions(a, b) {
  const A = parseVersion(a);
  const B = parseVersion(b);
  if (!A || !B) return NaN;
  if (A.major !== B.major) return A.major - B.major;
  if (A.minor !== B.minor) return A.minor - B.minor;
  if (A.patch !== B.patch) return A.patch - B.patch;
  if (!A.prerelease && !B.prerelease) return 0;
  if (!A.prerelease) return 1;  // 正式版 > prerelease
  if (!B.prerelease) return -1;
  const n = Math.max(A.prerelease.length, B.prerelease.length);
  for (let i = 0; i < n; i++) {
    if (i >= A.prerelease.length) return -1; // 前缀相同：更短 < 更长
    if (i >= B.prerelease.length) return 1;
    const d = cmpId(A.prerelease[i], B.prerelease[i]);
    if (d !== 0) return d;
  }
  return 0;
}

// ---------- registry 查询 ----------

// 默认 fetcher：node http/https，8s 超时；返回 {status, body}（网络错误 status=0）
function defaultFetcher(url, timeoutMs) {
  return new Promise((resolve) => {
    const mod = url.startsWith('https:') ? https : http;
    let settled = false;
    const finish = (v) => { if (!settled) { settled = true; resolve(v); } };
    const req = mod.get(url, { timeout: timeoutMs || 8000 }, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (d) => {
        body += d;
        if (body.length > 512 * 1024) { finish({ status: res.statusCode, body }); req.destroy(); }
      });
      res.on('end', () => finish({ status: res.statusCode, body }));
      res.on('error', () => finish({ status: 0, body: '' }));
    });
    req.on('timeout', () => { req.destroy(); finish({ status: 0, body: '' }); });
    req.on('error', () => finish({ status: 0, body: '' }));
  });
}

// 查 registry 的 @deepseek-ai/dsh latest 版本号；失败抛错（message 人类可读）
async function fetchLatestVersion(registryUrl, opts = {}) {
  const fetcher = opts.fetcher || defaultFetcher;
  const url = String(registryUrl).replace(/\/+$/, '') + '/@deepseek-ai/dsh/latest';
  const { status, body } = await fetcher(url, opts.timeoutMs);
  if (status !== 200) {
    throw new Error(status === 0 ? '网络请求失败' : 'registry 返回 HTTP ' + status);
  }
  let data;
  try { data = JSON.parse(body); } catch { throw new Error('registry 响应不是有效 JSON'); }
  const v = (data && (data.version || (data['dist-tags'] && data['dist-tags'].latest))) || null;
  if (!v) throw new Error('registry 响应缺少版本号');
  return String(v);
}

// ---------- 组装判定 ----------

// installedVersion 为 null（运行时未安装）→ 无需更新（首次安装本来就是最新）
async function checkForUpdate({ registry, installedVersion, fetcher, timeoutMs }) {
  if (!installedVersion) {
    return { ok: true, current: null, latest: null, hasUpdate: false, note: '内置运行时未安装，首次启动会自动安装最新版' };
  }
  let latest;
  try {
    latest = await fetchLatestVersion(registry, { fetcher, timeoutMs });
  } catch (e) {
    return { ok: false, current: installedVersion, latest: null, hasUpdate: false, error: e.message };
  }
  const c = compareVersions(installedVersion, latest);
  if (Number.isNaN(c)) {
    return { ok: false, current: installedVersion, latest, hasUpdate: false, error: '版本号无法解析（当前 ' + installedVersion + ' / 最新 ' + latest + '）' };
  }
  return { ok: true, current: installedVersion, latest, hasUpdate: c < 0 };
}

module.exports = { parseVersion, compareVersions, fetchLatestVersion, checkForUpdate, defaultFetcher };
