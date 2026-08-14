'use strict';

// update-check.js 单元测试：node test/update-check.test.js
// 覆盖：semver 比较语料（含 prerelease）+ 与捆绑 npm semver 对拍 + registry 查询注入桩 + 判定组装

const assert = require('assert');
const path = require('path');
const uc = require('../update-check.js');

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass++; console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' :: ' + e.message); }
}

// ---------- semver 比较语料 ----------
const pairs = [
  ['0.1.0', '0.1.0', 0],
  ['0.1.0', '0.1.1', -1],
  ['0.1.1', '0.1.0', 1],
  ['0.2.0', '0.1.99', 1],
  ['1.0.0', '0.9.9', 1],
  ['0.1.0-rc.6', '0.1.0-rc.6', 0],
  ['0.1.0-rc.6', '0.1.0-rc.7', -1],
  ['0.1.0-rc.10', '0.1.0-rc.6', 1],      // 数字段按数值
  ['0.1.0-rc.6', '0.1.0', -1],            // prerelease < 正式版
  ['0.1.0', '0.1.0-rc.6', 1],
  ['0.1.0-rc.6', '0.2.0', -1],            // 主次版本优先
  ['1.0.0-alpha', '1.0.0-alpha.1', -1],   // 前缀相同：短 < 长
  ['1.0.0-alpha.1', '1.0.0-alpha.beta', -1], // 数字 < 字母
  ['1.0.0-alpha.beta', '1.0.0-beta', -1],
  ['1.0.0-beta', '1.0.0-beta.2', -1],
  ['1.0.0-beta.2', '1.0.0-beta.11', -1],
  ['1.0.0-beta.11', '1.0.0-rc.1', -1],
  ['1.0.0-rc.1', '1.0.0', -1],
  ['v1.0.0', '1.0.0', 0],                 // 容忍 v 前缀
  ['1.0.0+build.5', '1.0.0', 0],          // build 元数据忽略
  ['not-a-version', '1.0.0', NaN],
];
t('semver 语料 ' + pairs.length + ' 组', () => {
  for (const [a, b, want] of pairs) {
    const got = uc.compareVersions(a, b);
    if (Number.isNaN(want)) assert(Number.isNaN(got), a + ' vs ' + b + ' 应为 NaN，实际 ' + got);
    else assert.strictEqual(Math.sign(got), want, a + ' vs ' + b + ' 应为 ' + want + '，实际 ' + got);
  }
});

// 与捆绑 npm semver 对拍（runtime-resources/npm/node_modules/semver）
t('与捆绑 npm semver 对拍', () => {
  const semverPath = path.join(__dirname, '..', 'runtime-resources', 'npm', 'node_modules', 'semver');
  let semver;
  try { semver = require(semverPath); } catch { console.log('  (捆绑 semver 不可用，跳过对拍)'); return; }
  const corpus = [
    '0.1.0', '0.1.0-rc.6', '0.1.0-rc.7', '0.1.0-rc.10', '0.2.0', '1.0.0',
    '1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-alpha.beta', '1.0.0-beta', '1.0.0-beta.2',
    '1.0.0-beta.11', '1.0.0-rc.1', '0.0.1', '2.0.0', '0.1.1',
  ];
  for (const a of corpus) {
    for (const b of corpus) {
      const mine = uc.compareVersions(a, b);
      const theirs = semver.compare(a, b);
      assert.strictEqual(Math.sign(mine), Math.sign(theirs), a + ' vs ' + b + ' 不一致: mine=' + mine + ' npm=' + theirs);
    }
  }
  console.log('  (' + corpus.length * corpus.length + ' 对全部一致)');
});

// ---------- fetchLatestVersion：注入 fetcher ----------
const stubFetcher = (status, body) => async (url) => ({ status, body });

t('fetch 成功（version 字段）', async () => {
  const v = await uc.fetchLatestVersion('https://registry.npmjs.org', { fetcher: stubFetcher(200, JSON.stringify({ name: '@deepseek-ai/dsh', version: '0.1.0-rc.6' })) });
  assert.strictEqual(v, '0.1.0-rc.6');
});
t('fetch 成功（dist-tags.latest，registry 尾斜杠归一）', async () => {
  let gotUrl = '';
  const fetcher = async (url) => { gotUrl = url; return { status: 200, body: JSON.stringify({ 'dist-tags': { latest: '0.2.0' } }) }; };
  const v = await uc.fetchLatestVersion('https://registry.npmmirror.com/', { fetcher });
  assert.strictEqual(v, '0.2.0');
  assert.strictEqual(gotUrl, 'https://registry.npmmirror.com/@deepseek-ai/dsh/latest');
});
t('fetch HTTP 404 → 抛错', async () => {
  await assert.rejects(() => uc.fetchLatestVersion('x', { fetcher: stubFetcher(404, 'not found') }), /HTTP 404/);
});
t('fetch 网络失败（status 0）→ 抛错', async () => {
  await assert.rejects(() => uc.fetchLatestVersion('x', { fetcher: stubFetcher(0, '') }), /网络请求失败/);
});
t('fetch 非法 JSON → 抛错', async () => {
  await assert.rejects(() => uc.fetchLatestVersion('x', { fetcher: stubFetcher(200, '<html>') }), /JSON/);
});
t('fetch 缺版本号 → 抛错', async () => {
  await assert.rejects(() => uc.fetchLatestVersion('x', { fetcher: stubFetcher(200, '{}') }), /版本号/);
});

// ---------- checkForUpdate 组装 ----------
t('已是最新 → hasUpdate=false', async () => {
  const r = await uc.checkForUpdate({ registry: 'r', installedVersion: '0.1.0-rc.6', fetcher: stubFetcher(200, JSON.stringify({ version: '0.1.0-rc.6' })) });
  assert.strictEqual(r.ok, true); assert.strictEqual(r.hasUpdate, false);
});
t('有新版 → hasUpdate=true', async () => {
  const r = await uc.checkForUpdate({ registry: 'r', installedVersion: '0.1.0-rc.6', fetcher: stubFetcher(200, JSON.stringify({ version: '0.1.0-rc.7' })) });
  assert.strictEqual(r.hasUpdate, true); assert.strictEqual(r.latest, '0.1.0-rc.7');
});
t('运行时未安装 → 无需更新', async () => {
  const r = await uc.checkForUpdate({ registry: 'r', installedVersion: null });
  assert.strictEqual(r.ok, true); assert.strictEqual(r.hasUpdate, false);
});
t('registry 失败 → ok=false + error', async () => {
  const r = await uc.checkForUpdate({ registry: 'r', installedVersion: '0.1.0', fetcher: stubFetcher(0, '') });
  assert.strictEqual(r.ok, false); assert(r.error);
});
t('版本号无法解析 → ok=false', async () => {
  const r = await uc.checkForUpdate({ registry: 'r', installedVersion: 'broken', fetcher: stubFetcher(200, JSON.stringify({ version: '0.1.0' })) });
  assert.strictEqual(r.ok, false); assert(/无法解析/.test(r.error));
});

console.log('\nRESULT: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail > 0 ? 1 : 0);
