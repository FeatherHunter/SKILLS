/**
 * dsh-waystation postinstall —— 自动注册到 DSH profile（npm 标准安装即自动完成，无需手动编辑）
 *
 * 行为：
 *   1. 定位 DSH profile 的 cordis.patch.yml：
 *      $DSH_HOME/profiles/web/cordis.patch.yml（DSH_HOME 未设 → ~/.dsh/profiles/web/…）
 *   2. 若文件不存在 → 跳过（非 DSH 环境，如普通项目里误装，不打扰）
 *   3. 若已包含 dsh-waystation 注册行 → 跳过（幂等，重复安装/升级不叠加）
 *   4. 否则在文件末尾追加注册块：
 *      - insert:
 *          - id: dsh-waystation
 *            name: 'dsh-waystation'
 *
 * 容错：任何异常只打印警告，绝不令 npm install 失败（postinstall 退出码恒 0）。
 */
const fs = require('fs')
const path = require('path')

function findPatchPath() {
  const home = process.env.DSH_HOME
    || (process.platform === 'win32' ? process.env.USERPROFILE : process.env.HOME)
  if (!home) return null
  return path.join(home, '.dsh', 'profiles', 'web', 'cordis.patch.yml')
}

const REGISTER_BLOCK =
  '\n# dsh-waystation：Waystation 控制面板（配合 mattpocock/skills 的 wayfinder 等技能）\n' +
  '# 自动注册（postinstall）· 包位于 profiles/node_modules/dsh-waystation\n' +
  '- insert:\n' +
  "    - id: dsh-waystation\n" +
  "      name: 'dsh-waystation'\n"

function main() {
  const patch = findPatchPath()
  if (!patch) {
    console.log('[dsh-waystation] 未找到 DSH_HOME，跳过自动注册（非 DSH 环境）')
    return
  }
  let existed = true
  let text = ''
  try {
    text = fs.readFileSync(patch, 'utf8')
  } catch (e) {
    existed = false // 文件不存在或不可读 → 视为需要创建
  }
  if (existed && /(?:id|name)\s*:\s*['"]?dsh-waystation['"]?/.test(text)) {
    console.log('[dsh-waystation] 已在 cordis.patch.yml 注册，跳过')
    return
  }
  try {
    fs.mkdirSync(path.dirname(patch), { recursive: true })
    fs.appendFileSync(patch, REGISTER_BLOCK, 'utf8')
    console.log('[dsh-waystation] 已自动注册到 ' + patch + '（刷新浏览器页面即生效）')
  } catch (e) {
    console.warn('[dsh-waystation] 自动注册失败（不影响本包安装）：' + String((e && e.message) || e))
  }
}

try {
  main()
} catch (e) {
  console.warn('[dsh-waystation] postinstall 异常（已忽略）：' + String((e && e.message) || e))
}
