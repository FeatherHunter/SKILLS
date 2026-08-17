#!/usr/bin/env node
/**
 * dsh-feishu-link · postinstall 自动注册 cordis.patch.yml
 *
 * 把本插件追加到 `~/.dsh/profiles/web/cordis.patch.yml`（或 DSH_HOME 指定的 home）。
 * 等幂：重复执行不影响。
 *
 * 实测教训（来自 waystation README）：pnpm 装包默认忽略 build scripts → postinstall 可能不执行。
 * 本脚本写法幂等 + 静默 + 给用户清楚的 console 提示，让用户可手动验证。
 */

const fs = require('fs')
const os = require('os')
const path = require('path')

function getDshHome() {
  if (process.env.DSH_HOME && process.env.DSH_HOME.trim()) return process.env.DSH_HOME.trim()
  // Windows 默认
  const userProfile = process.env.USERPROFILE || os.homedir()
  return path.join(userProfile, '.dsh')
}

function getPatchFile(dshHome) {
  return path.join(dshHome, 'profiles', 'web', 'cordis.patch.yml')
}

function readIfExists(p) {
  try { return fs.readFileSync(p, 'utf8') } catch (_) { return '' }
}

function ensureParentDir(filePath) {
  const dir = path.dirname(filePath)
  fs.mkdirSync(dir, { recursive: true })
}

function appendPatch(patchFile, pluginId, pluginName) {
  const existed = readIfExists(patchFile)
  // 已包含则跳过
  if (existed && existed.indexOf('- id: ' + pluginId) >= 0) {
    console.log('[dsh-feishu-link] postinstall: already registered (id=' + pluginId + '), skip')
    return false
  }
  ensureParentDir(patchFile)
  // 如果文件不存在或为空，先写头部（虽然 patch.yml 不一定需要头部，但保险）
  const initial = (existed && existed.trim().length > 0) ? '' : '# dsh cordis patch (auto-managed by dsh-feishu-link)\n'
  const block = [
    initial,
    '# inserted by dsh-feishu-link postinstall (' + new Date().toISOString() + ')',
    '- insert:',
    '    - id: ' + pluginId,
    "      name: '" + pluginName + "'",
    '',
  ].join('\n')
  fs.appendFileSync(patchFile, block, 'utf8')
  console.log('[dsh-feishu-link] postinstall: registered id=' + pluginId + ' in ' + patchFile)
  return true
}

function main() {
  const dshHome = getDshHome()
  const patchFile = getPatchFile(dshHome)
  appendPatch(patchFile, 'dsh-feishu-link', 'dsh-feishu-link')
}

try { main() } catch (e) {
  console.warn('[dsh-feishu-link] postinstall failed (non-fatal):', (e && e.message) || e)
  console.warn('  你可手动追加到 ~/.dsh/profiles/web/cordis.patch.yml：')
  console.warn('  - insert:')
  console.warn('      - id: dsh-feishu-link')
  console.warn("        name: 'dsh-feishu-link'")
  process.exit(0)  // postinstall 失败不阻断 npm install
}
