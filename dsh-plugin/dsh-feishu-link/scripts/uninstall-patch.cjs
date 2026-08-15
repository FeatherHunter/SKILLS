#!/usr/bin/env node
/**
 * dsh-feishu-link · uninstall-patch · 移除 patch 段
 *
 * 与 install-patch.cjs 对称。在 npm uninstall 时执行：
 *   - 从 `~/.dsh/profiles/web/cordis.patch.yml` 移除 - insert: 块（以 - id: dsh-feishu-link 为锚点）
 *   - 不动其他插件条目（幂等）
 *   - 失败静默不阻断
 *
 * v0.2+ 由 package.json 的 `uninstall` script 自动调用。
 */

const fs = require('fs')
const os = require('os')
const path = require('path')

function getDshHome() {
  if (process.env.DSH_HOME && process.env.DSH_HOME.trim()) return process.env.DSH_HOME.trim()
  return path.join(process.env.USERPROFILE || os.homedir(), '.dsh')
}

function getPatchFile(dshHome) {
  return path.join(dshHome, 'profiles', 'web', 'cordis.patch.yml')
}

function main() {
  const dshHome = getDshHome()
  const patchFile = getPatchFile(dshHome)
  if (!fs.existsSync(patchFile)) {
    console.log('[dsh-feishu-link] uninstall: no patch file, nothing to do')
    return
  }
  const original = fs.readFileSync(patchFile, 'utf8')
  const lines = original.split(/\r?\n/)
  // 扫描块：从一个 '# inserted by dsh-feishu-link ...' 注释到下一个完全空白行
  const out = []
  let skipUntilBlank = false
  let stripped = 0
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i]
    if (skipUntilBlank) {
      // 当前块正在被跳过。遇到以 '- id: ' 开头但非 dsh-feishu-link 的行 → 视为新块开始，要重新开启"包含"
      if (/^\s*-\s+id:/.test(ln) && !/dsh-feishu-link/.test(ln)) {
        skipUntilBlank = false
        out.push(ln)
        continue
      }
      // 遇完全空白行 → 块结束
      if (ln.trim() === '') {
        skipUntilBlank = false
      }
      stripped++
      continue
    }
    // 待识别块起点：注释 + 紧跟 - insert: 块 + 里面有 dsh-feishu-link
    if (/^\s*#\s*inserted by dsh-feishu-link/.test(ln)) {
      // 接下来连同 - insert: 整块跳过，直到空白行结束
      skipUntilBlank = true
      stripped++
      continue
    }
    out.push(ln)
  }
  if (stripped > 0) {
    fs.writeFileSync(patchFile, out.join('\n'), 'utf8')
    console.log('[dsh-feishu-link] uninstall: removed patch entry from ' + patchFile + ' (' + stripped + ' lines)')
  } else {
    console.log('[dsh-feishu-link] uninstall: no patch entry to remove')
  }
}

try { main() } catch (e) {
  console.warn('[dsh-feishu-link] uninstall failed (non-fatal):', (e && e.message) || e)
  process.exit(0)
}
