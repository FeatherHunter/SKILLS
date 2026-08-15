#!/usr/bin/env node
/**
 * dsh-feishu-link · release.mjs · 一键 bump version + 同步 CHANGELOG + tag
 *
 * 跑：node scripts/release.mjs patch | minor | major
 *
 * 逻辑：
 *   1. bump package.json version
 *   2. 在 CHANGELOG.md 顶部追加 "## [new version]" 段头
 *   3. 在 README.md 底部追加 "## Download · <version>" 段（如果有）
 *   4. git tag v<version>
 *
 * 不自动 push（用户决定）。
 */

import fs from 'node:fs'
import path from 'node:path'
import { execSync } from 'node:child_process'

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'))
}
function writeJson(p, data) {
  fs.writeFileSync(p, JSON.stringify(data, null, 2) + '\n', 'utf8')
}
function bump(currentVersion, type) {
  const m = currentVersion.match(/^(\d+)\.(\d+)\.(\d+)(-.*)?$/)
  if (!m) throw new Error('invalid version: ' + currentVersion)
  let [, ma, mi, pa, pre] = [null, +m[1], +m[2], +m[3], m[4] || '']
  if (type === 'major') { ma++; mi = 0; pa = 0 }
  else if (type === 'minor') { mi++; pa = 0 }
  else if (type === 'patch') { pa++ }
  else throw new Error('unknown bump type: ' + type)
  return `${ma}.${mi}.${pa}${pre}`
}

const type = process.argv[2] || 'patch'
const pkgPath = path.resolve('package.json')
const pkg = readJson(pkgPath)
const oldVer = pkg.version
const newVer = bump(oldVer, type)
console.log(`[release] bump ${oldVer} -> ${newVer} (${type})`)

pkg.version = newVer
writeJson(pkgPath, pkg)

// CHANGELOG.md 顶部追加
const changelogPath = path.resolve('CHANGELOG.md')
if (fs.existsSync(changelogPath)) {
  const cur = fs.readFileSync(changelogPath, 'utf8')
  const today = new Date().toISOString().slice(0, 10)
  const newSection = `## [${newVer}] · ${today}\n\n### Changed\n\n- Released version ${newVer}\n\n`
  fs.writeFileSync(changelogPath, newSection + cur, 'utf8')
  console.log(`[release] prepended CHANGELOG section for ${newVer}`)
}

// git add + commit + tag
try {
  execSync(`git add package.json CHANGELOG.md`, { stdio: 'inherit' })
  execSync(`git commit -m "[dsh-feishu-link] bump v${newVer}"`, { stdio: 'inherit' })
  execSync(`git tag -a "v${newVer}" -m "v${newVer}"`, { stdio: 'inherit' })
  console.log(`[release] git tag v${newVer} created (run 'git push --tags' to publish)`)
} catch (e) {
  console.warn('[release] git ops failed:', (e && e.message) || e)
}

console.log(`[release] done. version = v${newVer}`)
