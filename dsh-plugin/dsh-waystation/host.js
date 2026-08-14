/**
 * DSH-Waystation · Host 半（数据层实现 · T3 #345）
 *
 * 实现：
 *   1. gh 封装层：resolveExecutable 解析 → 兜底 D:\0Tools\GitHubCLI\gh.exe；30s 超时（timer race + terminate）；
 *      错误归一化（auth / network / notfound / exit）。
 *   2. 数据流：gh issue list 枚举 wayfinder:map → 每 map 一次 GraphQL（subIssues + labels + assignees +
 *      blockedBy + blocking）→ 组装快照（map 五区块解析 + tickets + stats 分组）。
 *   3. RPC：wf.ping / wf.snapshot（5s 缓存）/ wf.refresh。
 *   4. 轮询：timer 60s 刷新缓存 + 与上次 stats diff（P2 toast 预留字段）。
 *   5. 前置检查绿点（#344）：wf.status —— 8 项检测（仓库定位 / setup 已跑 / tracker=GitHub /
 *      gh CLI / gh 登录 / API 可达 / wayfinder 双层探测 / ask-matt 双层探测），输出
 *      { ok, level, detail, hint }[]；结果缓存 30s，args.force 强制重查。
 *
 * 已验证（.charting/verify.js，真实数据 PASS）：分组 frontier/claimed/blocked 与 GitHub 页面一致；
 * 9 张 open map 中仅 4 张有 Destination —— body 解析全部容错。
 *
 * 本文件内容 = cordis_define 的 code.host（纯 JS 函数体，返回 Cordis Plugin）。
 */
return {
  apply(ctx) {
    const subprocess = ctx.get('subprocess')
    const timer = ctx.get('timer')
    const fs = ctx.get('fs')
    if (subprocess === undefined || timer === undefined) return

    // ============ 配置 ============
    const GH_FALLBACK = 'D:\\0Tools\\GitHubCLI\\gh.exe'   // 本仓库实测 gh 不在 PATH（docs/agents/issue-tracker.md）
    const DEFAULT_CWD = 'D:\\2Study\\StudyNotes\\SKILLS'  // 默认工作区；可被 wf.snapshot args.cwd 覆盖
    const TIMEOUT_MS = 30000
    const CACHE_MS = 5000
    const STATUS_CACHE_MS = 30000  // 前置检查结果缓存（#344）
    const SKILL_PROBE_DIRS = ['.agents\\skills', '.minimax\\skills', '.claude\\skills']  // 技能文件层探测目录（相对用户主目录）
    const SKILL_PROBE_NAMES = ['wayfinder', 'ask-matt']  // 技能探测名单（#344 检查 7/8）
    const QUERY = 'query($owner:String!,$name:String!,$n:Int!){repository(owner:$owner,name:$name){issue(number:$n){number title state body url labels(first:20){nodes{name}} subIssues(first:100){totalCount nodes{number title state url labels(first:10){nodes{name}} assignees(first:10){nodes{login}} blockedBy(first:20){nodes{number title state}} }}}}}'

    // ============ 状态 ============
    let ghPath = null
    let ghPathError = null
    let repoKeys = {}  // v12：repoKey 按 cwd 缓存（切换仓库会话时不再串仓库）
    let cache = { ts: 0, snapshot: null, error: null, cwd: null }
    let statusCache = { ts: 0, status: null, error: null, cwd: null }  // wf.status 30s 缓存（按 cwd 区分）
    let userHome = null                                     // 用户主目录（cmd 探测，缓存）

    // ============ gh 封装 ============
    async function resolveGh() {
      if (ghPath) return ghPath
      if (ghPathError) return null
      try {
        ghPath = await subprocess.resolveExecutable('gh')
      } catch (e) {
        // 兜底：fs.lstat 对不存在路径返回 undefined（不抛错），须判真值（#344 修正）
        let info = null
        try {
          if (fs !== undefined) info = await fs.lstat(GH_FALLBACK)
          else ghPathError = 'gh 不可用：PATH 无 gh 且 fs 服务不可用'
        } catch (e2) {
          info = null
        }
        if (info) ghPath = GH_FALLBACK
        else ghPathError = 'gh 不可用：PATH 无 gh，且 ' + GH_FALLBACK + ' 不存在（环境检查 #4）'
      }
      return ghPath
    }

    async function runGh(args, cwd) {
      const exe = await resolveGh()
      if (!exe) return { ok: false, kind: 'env', error: ghPathError }
      let handle
      try {
        handle = subprocess.spawn({
          argv: [exe].concat(args),
          cwd: cwd || DEFAULT_CWD,
          stdio: { stdin: 'ignore', stdout: { maxBytes: 4 * 1024 * 1024 }, stderr: { maxBytes: 256 * 1024 } },
          graceMs: 2000,
        })
      } catch (e) {
        return { ok: false, kind: 'spawn', error: String((e && e.message) || e) }
      }
      const to = timer.timeout(TIMEOUT_MS)
      let outcome
      try {
        outcome = await Promise.race([
          handle.done,
          to.then(function () { handle.terminate(); return { exitCode: -1, signal: 'timeout' } }),
        ])
      } catch (e) {
        return { ok: false, kind: 'spawn', error: String((e && e.message) || e) }
      }
      const out = (handle.collected && handle.collected.stdout) ? handle.collected.stdout.readFrom(0) : { text: '' }
      const err = (handle.collected && handle.collected.stderr) ? handle.collected.stderr.readFrom(0) : { text: '' }
      const all = (err.text || '') + (out.text || '')
      if (outcome.exitCode !== 0) {
        let kind = 'exit'
        const t = all.toLowerCase()
        if (/not logged in|auth failed|bad credentials/i.test(t)) kind = 'auth'
        else if (/404|not found|could not resolve to an? (issue|pull request)/i.test(t)) kind = 'notfound'
        else if (/network|econn|unexpected eof|timed out|connect/i.test(t)) kind = 'network'
        return { ok: false, kind: kind, code: outcome.exitCode, error: all.slice(0, 400) }
      }
      return { ok: true, text: out.text || '' }
    }

    // 通用进程执行（#344 前置检查用：git / cmd 等，不经 shell，错误不归一化）
    async function execProc(argv, cwd) {
      let handle
      try {
        handle = subprocess.spawn({
          argv: argv,
          cwd: cwd || DEFAULT_CWD,
          stdio: { stdin: 'ignore', stdout: { maxBytes: 1024 * 1024 }, stderr: { maxBytes: 256 * 1024 } },
          graceMs: 2000,
        })
      } catch (e) {
        return { ok: false, error: String((e && e.message) || e) }
      }
      const to = timer.timeout(TIMEOUT_MS)
      let outcome
      try {
        outcome = await Promise.race([
          handle.done,
          to.then(function () { handle.terminate(); return { exitCode: -1, signal: 'timeout' } }),
        ])
      } catch (e) {
        return { ok: false, error: String((e && e.message) || e) }
      }
      const out = (handle.collected && handle.collected.stdout) ? handle.collected.stdout.readFrom(0) : { text: '' }
      const err = (handle.collected && handle.collected.stderr) ? handle.collected.stderr.readFrom(0) : { text: '' }
      if (outcome.exitCode !== 0) return { ok: false, code: outcome.exitCode, error: ((err.text || '') + (out.text || '')).slice(0, 400) }
      return { ok: true, text: out.text || '' }
    }

    async function resolveGit() {
      try { return await subprocess.resolveExecutable('git') } catch (e) { return null }
    }

    // 用户主目录（Windows 实测 cmd.exe 恒在；POSIX 可走 sh -c 'echo $HOME'，本插件以 Windows 为主）
    async function getHome() {
      if (userHome !== null) return userHome
      userHome = null
      try {
        const cmd = await subprocess.resolveExecutable('cmd.exe')
        if (!cmd) return null
        const r = await execProc([cmd, '/c', 'echo', '%USERPROFILE%'], DEFAULT_CWD)
        if (r.ok) {
          const v = r.text.trim()
          if (v && /[\\/]/.test(v)) userHome = v
        }
      } catch (e) { userHome = null }
      return userHome
    }

    async function getRepoKey(cwd) {
      const key = cwd || DEFAULT_CWD
      if (repoKeys[key]) return repoKeys[key]
      const r = await runGh(['repo', 'view', '--json', 'nameWithOwner', '-q', '.nameWithOwner'], key)
      if (!r.ok) return null
      const s = r.text.trim()
      const i = s.indexOf('/')
      if (i <= 0) return null
      repoKeys[key] = { owner: s.slice(0, i), name: s.slice(i + 1) }
      return repoKeys[key]
    }

    // ============ 数据流 ============
    function parseMapBody(body) {
      const out = { destination: '', notes: '', decisions: [], fog: [], outOfScope: [] }
      if (!body) return out
      const sec = {}
      const lines = String(body).split(/\r?\n/)
      let cur = null
      for (let i = 0; i < lines.length; i++) {
        const m = lines[i].match(/^##\s+(.+?)\s*$/)
        if (m) { cur = m[1]; sec[cur] = sec[cur] || []; continue }
        if (cur) sec[cur].push(lines[i])
      }
      const clean = function (arr) { return (arr || []).map(function (s) { return s.trim() }).filter(Boolean) }
      out.destination = clean(sec['Destination']).join(' ')
      out.notes = clean(sec['Notes']).join(' ')
      out.decisions = clean(sec['Decisions so far']).filter(function (l) { return l.indexOf('- [') === 0 }).map(function (l) {
        const t = l.match(/\[(.+?)\]\((.+?)\)/)
        const g = l.replace(/^-\s*\[.+?\]\(.+?\)\s*[-–—]?\s*/, '')
        return { title: t ? t[1] : l, url: t ? t[2] : '', gist: g }
      })
      out.fog = clean(sec['Not yet specified']).filter(function (l) { return l.indexOf('<!--') !== 0 })
      out.outOfScope = clean(sec['Out of scope']).filter(function (l) { return l.indexOf('<!--') !== 0 })
      return out
    }

    function mapTicket(raw) {
      const labels = ((raw.labels && raw.labels.nodes) || []).map(function (x) { return x.name })
      let type = 'other'
      for (let i = 0; i < labels.length; i++) {
        if (labels[i].indexOf('wayfinder:') === 0) { type = labels[i].slice('wayfinder:'.length) || 'other'; break }
      }
      const as = (raw.assignees && raw.assignees.nodes) || []
      return {
        number: raw.number, title: raw.title, type: type,
        state: raw.state === 'CLOSED' ? 'CLOSED' : 'OPEN',
        claimedBy: as.length ? as[0].login : '',
        blockedBy: ((raw.blockedBy && raw.blockedBy.nodes) || []).map(function (b) { return b.number }),
        blocks: ((raw.blocking && raw.blocking.nodes) || []).map(function (b) { return b.number }),
        labels: labels, url: raw.url,
      }
    }

    function groupTickets(tickets) {
      const byNum = {}
      tickets.forEach(function (t) { byNum[t.number] = t })
      const openBlocker = function (b) { const t = byNum[b]; return t !== undefined && t.state === 'OPEN' }
      const open = tickets.filter(function (t) { return t.state === 'OPEN' })
      const closed = tickets.filter(function (t) { return t.state === 'CLOSED' })
      const frontier = open.filter(function (t) { return !t.claimedBy && !t.blockedBy.some(openBlocker) })
      const claimed = open.filter(function (t) { return t.claimedBy })
      const blocked = open.filter(function (t) { return !t.claimedBy && t.blockedBy.some(openBlocker) })
      return {
        total: tickets.length, open: open.length, closed: closed.length,
        frontier: frontier.length, claimed: claimed.length, blocked: blocked.length,
      }
    }

    async function fetchMaps(cwd) {
      const r = await runGh(['issue', 'list', '--state', 'open', '--label', 'wayfinder:map', '--json', 'number,title,body,labels,assignees,state,updatedAt'], cwd)
      if (!r.ok) return { ok: false, error: r }
      try { return { ok: true, maps: JSON.parse(r.text) } } catch (e) { return { ok: false, error: { kind: 'parse', error: String(e) } } }
    }

    // 全部 issue（open + closed，Client 列表 open 常显、底部「已关闭」折叠行），
    // 按 updatedAt 倒序；labels 带 name + color（GitHub 配置色）；state 区分 open/closed；
    // v18：assignees 带出（状态栏「占用」按列表 issue 口径：已认领 + 被阻塞）
    async function fetchIssues(cwd) {
      // #374/#375：--limit 500 覆盖仓库全量（2026-08-14 实测 349 issue），并带出 createdAt（排序维度）
      const r = await runGh(['issue', 'list', '--state', 'all', '--limit', '500', '--json', 'number,title,labels,state,assignees,updatedAt,createdAt'], cwd)
      if (!r.ok) return { ok: false, error: r }
      try {
        const all = JSON.parse(r.text)
        const issues = all.map(function (x) {
          return {
            number: x.number,
            title: x.title,
            state: x.state,
            assignees: (x.assignees || []).map(function (a) { return a.login }),
            labels: (x.labels || []).map(function (l) { return { name: l.name, color: l.color || '' } }),
            updatedAt: x.updatedAt,
            createdAt: x.createdAt,
          }
        })
        issues.sort(function (a, b) { return String(b.updatedAt).localeCompare(String(a.updatedAt)) })
        return { ok: true, issues: issues }
      } catch (e) { return { ok: false, error: { kind: 'parse', error: String(e) } } }
    }

    async function fetchMapDetail(number, cwd) {
      const repo = await getRepoKey(cwd)
      if (!repo) return { ok: false, error: { kind: 'env', error: '无法解析 owner/repo（git remote 或 gh repo view 失败）' } }
      // 网络类失败重试 1 次（实测 api.github.com 偶发 EOF；其他错误直接返回）
      let last = null
      for (let attempt = 0; attempt < 2; attempt++) {
        const r = await runGh(['api', 'graphql', '-f', 'query=' + QUERY, '-F', 'owner=' + repo.owner, '-F', 'name=' + repo.name, '-F', 'n=' + String(number)])
        if (!r.ok) {
          last = r
          if (r.kind !== 'network') return { ok: false, error: r }
          continue
        }
        try {
          const j = JSON.parse(r.text)
          if (j.errors) return { ok: false, error: { kind: 'graphql', error: JSON.stringify(j.errors).slice(0, 300) } }
          return { ok: true, issue: j.data.repository.issue }
        } catch (e) { return { ok: false, error: { kind: 'parse', error: String(e) } } }
      }
      return { ok: false, error: last || { kind: 'network', error: 'GraphQL 请求失败（重试后仍失败）' } }
    }

    async function buildSnapshot(cwd) {
      const repo = await getRepoKey(cwd)
      const fm = await fetchMaps(cwd)
      if (!fm.ok) throw fm.error
      const fi = await fetchIssues(cwd)
      const issues = fi.ok ? fi.issues : []
      // #375：全量 label 列表（含空 label；获取失败容错置空，不阻塞快照构建，client 降级）
      let labels = []
      const fl = await runGh(['label', 'list', '--json', 'name,color'], cwd)
      if (fl.ok) {
        try {
          const ls = JSON.parse(fl.text)
          if (Array.isArray(ls)) labels = ls.map(function (l) { return { name: l.name, color: l.color || '' } })
        } catch (e) { labels = [] }
      }
      // 并行拉取各 map 详情（Promise.all 保序输出；实测串行 7 map ≈ 10s → 并行 ≈ 3s）
      const details = await Promise.all(fm.maps.map(function (m) { return fetchMapDetail(m.number, cwd) }))
      const maps = []
      for (let i = 0; i < fm.maps.length; i++) {
        const m = fm.maps[i]
        const d = details[i]
        if (!d.ok) {
          maps.push({ number: m.number, title: m.title, state: m.state, error: d.error, tickets: [], stats: { total: 0, open: 0, closed: 0, frontier: 0, claimed: 0, blocked: 0 } })
          continue
        }
        const issue = d.issue
        const subs = (issue.subIssues && issue.subIssues.nodes) || []
        const tickets = subs.map(mapTicket)
        const bp = parseMapBody(issue.body)
        const stats = groupTickets(tickets)
        const labels = ((issue.labels && issue.labels.nodes) || []).map(function (x) { return x.name })
        maps.push({
          number: issue.number, title: issue.title, state: issue.state, url: issue.url, labels: labels,
          destination: bp.destination, notes: bp.notes,
          decisions: bp.decisions, fog: bp.fog, outOfScope: bp.outOfScope,
          tickets: tickets, stats: stats,
        })
      }
      return {
        ok: true,
        repo: repo,
        updatedAt: new Date().toISOString(),
        generatedMs: Date.now(),
        env: { ghPath: ghPath, ghError: ghPathError },
        maps: maps,
        issues: issues,
        labels: labels,
      }
    }

    // ============ 前置检查（#344 · wf.status）============
    // 解析 git 远程 URL → GitHub owner/repo；非 GitHub 返回 null
    function parseGithubRepo(url) {
      const s = String(url || '').trim()
      const m = s.match(/github\.com[\/:]([^\/\s]+)\/([^\/\s]+?)(?:\.git)?\s*$/)
      if (!m) return null
      return { owner: m[1], name: m[2] }
    }

    // 检查 1 · 仓库定位
    async function checkRepo(cwd) {
      const git = await resolveGit()
      if (git) {
        const r = await execProc([git, '-C', cwd, 'remote', 'get-url', 'origin'], cwd)
        if (r.ok) {
          const key = parseGithubRepo(r.text)
          if (key) return { ok: true, level: 'ok', detail: key.owner + '/' + key.name, hint: '', repo: key }
          return { ok: true, level: 'warn', detail: '有 git 远程但非 GitHub：' + r.text.trim().slice(0, 80), hint: '当前远程不是 GitHub', repo: null }
        }
        if (/not a git repository|does not appear to be a git repository|fatal/i.test(r.error || '')) {
          return { ok: false, level: 'bad', detail: '当前目录不是 git 仓库', hint: '在 GitHub 仓库内使用本插件', repo: null }
        }
        return { ok: false, level: 'bad', detail: 'git 查询失败：' + String(r.error || '').slice(0, 120), hint: '检查 git 与仓库状态', repo: null }
      }
      // 兜底：解析 .git/config（git 可执行不可用时）
      if (fs !== undefined) {
        try {
          const t = await fs.resolve('.git/config', { cwd: cwd })
          const txt = await fs.readText(t)
          const um = txt.match(/url\s*=\s*(.+)/)
          if (um) {
            const key = parseGithubRepo(um[1])
            if (key) return { ok: true, level: 'ok', detail: key.owner + '/' + key.name, hint: '', repo: key }
            return { ok: true, level: 'warn', detail: '有 git 远程但非 GitHub：' + um[1].trim().slice(0, 80), hint: '当前远程不是 GitHub', repo: null }
          }
        } catch (e) { /* 落到下方 bad */ }
      }
      return { ok: false, level: 'bad', detail: '无法定位仓库（git 不可用且无 .git/config）', hint: '在 GitHub 仓库内使用本插件', repo: null }
    }

    // 检查 2 · setup 已执行
    async function checkSetup(cwd) {
      if (fs === undefined) return { ok: false, level: 'bad', detail: 'fs 服务不可用，无法检测', hint: '请先运行 /setup-matt-pocock-skills', repo: null }
      try {
        const info = await fs.lstat('docs/agents/issue-tracker.md', { cwd: cwd })
        if (info) return { ok: true, level: 'ok', detail: 'docs/agents/issue-tracker.md 存在', hint: '', repo: null }
      } catch (e) { /* 落到下方 bad */ }
      return { ok: false, level: 'bad', detail: 'docs/agents/issue-tracker.md 不存在', hint: '请先运行 /setup-matt-pocock-skills', repo: null }
    }

    // 检查 3 · tracker = GitHub
    async function checkTracker(cwd) {
      if (fs === undefined) return { ok: false, level: 'bad', detail: 'fs 服务不可用，无法判定 tracker', hint: '请先运行 /setup-matt-pocock-skills', repo: null }
      try {
        const t = await fs.resolve('docs/agents/issue-tracker.md', { cwd: cwd })
        const txt = await fs.readText(t)
        if (/github/i.test(txt) && /gh\s+(issue|api|auth)|GitHub Issues/i.test(txt)) {
          return { ok: true, level: 'ok', detail: 'GitHub Issues + gh CLI', hint: '', repo: null }
        }
        return { ok: false, level: 'warn', detail: 'issue-tracker.md 存在但非 GitHub 模板', hint: '运行 /setup-matt-pocock-skills 重选 GitHub tracker', repo: null }
      } catch (e) {
        return { ok: false, level: 'bad', detail: '无法读取 issue-tracker.md', hint: '请先运行 /setup-matt-pocock-skills', repo: null }
      }
    }

    // 检查 4 · gh CLI 可用
    async function checkGhCli() {
      const exe = await resolveGh()
      if (!exe) return { ok: false, level: 'bad', detail: ghPathError || 'gh 未找到', hint: '安装 GitHub CLI，或配置兜底路径', repo: null }
      return { ok: true, level: 'ok', detail: exe, hint: '', repo: null }
    }

    // 检查 5 · gh 已登录
    async function checkGhAuth() {
      const r = await runGh(['auth', 'status'])
      if (r.ok) {
        const first = (r.text || '').split(/\r?\n/).map(function (s) { return s.trim() }).filter(Boolean)[0]
        return { ok: true, level: 'ok', detail: first || '已登录', hint: '', repo: null }
      }
      return { ok: false, level: 'bad', detail: 'gh auth status 失败（' + r.kind + '）', hint: '运行 gh auth login', repo: null }
    }

    // 检查 6 · API 可达（有 repo 用 repos/<owner>/<name>，否则退 user）
    async function checkApi(cwd, repo) {
      const endpoint = repo ? ('repos/' + repo.owner + '/' + repo.name) : 'user'
      const r = await runGh(['api', endpoint], cwd)
      if (r.ok) return { ok: true, level: 'ok', detail: 'api.github.com 200 · ' + endpoint, hint: '', repo: null }
      return { ok: false, level: 'bad', detail: 'API 请求失败（' + r.kind + '）', hint: '检查网络 / Token 权限', repo: null }
    }

    // 检查 7/8 · 技能安装探测（#373 拍板：两态 —— 已安装/未安装；去掉不可靠的「挂载」判定：
    //   宿主级 skills 服务与「当前会话挂载」不是同一上下文，服务不可用时会误报「未挂载」）
    const SKILL_INSTALL_URL = 'https://github.com/mattpocock/skills'
    async function probeSkill(name) {
      let session = false
      const skills = ctx.get('skills')
      if (skills !== undefined) {
        try { session = !!(await skills.get(name)) } catch (e) { session = false }
      }
      let fsFound = null
      const home = await getHome()
      if (fs !== undefined && home) {
        for (let i = 0; i < SKILL_PROBE_DIRS.length; i++) {
          try {
            const info = await fs.lstat(home + '\\' + SKILL_PROBE_DIRS[i] + '\\' + name)
            if (info) { fsFound = '~/' + SKILL_PROBE_DIRS[i] + '/' + name; break }
          } catch (e) { /* 继续探测下一个目录 */ }
        }
      }
      // 两态：#373 —— 任一来源发现 = 已安装（绿 ok）；均无 = 未安装（红 bad + 官方仓库地址）
      if (session && fsFound) return { ok: true, level: 'ok', detail: '已安装（会话已挂载 · ' + fsFound + '）', hint: '', repo: null }
      if (session) return { ok: true, level: 'ok', detail: '已安装（会话已挂载）', hint: '', repo: null }
      if (fsFound) return { ok: true, level: 'ok', detail: '已安装（' + fsFound + '）', hint: '', repo: null }
      if (home === null) return { ok: false, level: 'bad', detail: '未安装（无法探测用户主目录）', hint: SKILL_INSTALL_URL, repo: null }
      return { ok: false, level: 'bad', detail: '未安装', hint: SKILL_INSTALL_URL, repo: null }
    }

    const CHECK_NAMES = ['仓库定位', 'setup 已执行', 'tracker = GitHub', 'gh CLI 可用', 'gh 已登录', 'API 可达', 'wayfinder 技能', 'ask-matt 技能']

    async function buildStatus(cwd) {
      const c1 = await checkRepo(cwd)
      const c2 = await checkSetup(cwd)
      const c3 = await checkTracker(cwd)
      const c4 = await checkGhCli()
      const c5 = await checkGhAuth()
      const c6 = await checkApi(cwd, c1.repo)
      const c7 = await probeSkill(SKILL_PROBE_NAMES[0])
      const c8 = await probeSkill(SKILL_PROBE_NAMES[1])
      const raw = [c1, c2, c3, c4, c5, c6, c7, c8]
      const checks = raw.map(function (c, i) {
        return { id: i + 1, name: CHECK_NAMES[i], ok: c.level === 'ok', level: c.level, detail: c.detail, hint: c.hint }
      })
      return {
        ok: true,
        updatedAt: new Date().toISOString(),
        cwd: cwd,
        repo: c1.repo,
        ghPath: ghPath,
        checks: checks,
        ready: checks.filter(function (c) { return c.ok }).length,
        total: checks.length,
      }
    }

    // ============ RPC ============
    harness.handle('wf.status', async function (args) {
      const cwd = (args && args.cwd) || DEFAULT_CWD
      const force = !!(args && args.force)
      const now = Date.now()
      if (!force && statusCache.status && statusCache.cwd === cwd && now - statusCache.ts < STATUS_CACHE_MS) return statusCache.status
      try {
        const status = await buildStatus(cwd)
        statusCache = { ts: Date.now(), status: status, error: null, cwd: cwd }
        return status
      } catch (e) {
        statusCache = { ts: Date.now(), status: null, error: String((e && e.message) || e), cwd: cwd }
        return { ok: false, error: String((e && e.message) || e), checks: [], ready: 0, total: CHECK_NAMES.length }
      }
    })

    harness.handle('wf.ping', async function () {
      return { ok: true, ts: Date.now() }
    })

    // v13：按 sessionId 反查会话工作目录（client 切换对话时用；宿主 sessions.meta 是权威字段，
    // 不再依赖 client 猜测 ConversationSnapshot 字段名）
    harness.handle('wf.cwd', async function (args) {
      const sid = args && args.sessionId
      if (!sid) return { ok: false, error: '缺少 sessionId' }
      const sessions = ctx.get('sessions')
      if (sessions === undefined || typeof sessions.get !== 'function') return { ok: false, error: 'sessions 服务不可用' }
      try {
        const s = sessions.get(sid)
        const meta = s && s.meta
        const cwd = meta && (meta.cwd || meta.path || meta.worktree || meta.projectDir || meta.directory)
        if (typeof cwd === 'string' && cwd) return { ok: true, cwd: cwd }
        return { ok: false, error: '会话无 cwd 信息' }
      } catch (e) {
        return { ok: false, error: String((e && e.message) || e) }
      }
    })

    harness.handle('wf.snapshot', async function (args) {
      const cwd = (args && args.cwd) || DEFAULT_CWD
      const now = Date.now()
      if (cache.snapshot && cache.cwd === cwd && now - cache.ts < CACHE_MS) return cache.snapshot
      try {
        const snap = await buildSnapshot(cwd)
        cache = { ts: Date.now(), snapshot: snap, error: null, cwd: cwd }
        return snap
      } catch (e) {
        cache = { ts: Date.now(), snapshot: null, error: String((e && e.message) || e), cwd: cwd }
        return { ok: false, error: String((e && e.message) || e), env: { ghError: ghPathError } }
      }
    })

    harness.handle('wf.refresh', async function (args) {
      const cwd = (args && args.cwd) || DEFAULT_CWD
      try {
        const snap = await buildSnapshot(cwd)
        cache = { ts: Date.now(), snapshot: snap, error: null, cwd: cwd }
        return snap
      } catch (e) {
        cache = { ts: Date.now(), snapshot: null, error: String((e && e.message) || e), cwd: cwd }
        return { ok: false, error: String((e && e.message) || e) }
      }
    })

    // v19：查询 .scratch/handoff/ 下最新的交接文档（按 mtime 倒序），供「交接给新会话」预填 + 复制
    harness.handle('wf.handoffLatest', async function (args) {
      const cwd = (args && args.cwd) || DEFAULT_CWD
      if (fs === undefined) return { ok: false, error: 'fs 服务不可用' }
      try {
        const dir = await fs.resolve('.scratch/handoff', { cwd: cwd })
        const entries = await fs.listDir(dir)
        const mds = []
        for (let i = 0; i < entries.length; i++) {
          const e = entries[i]
          const name = (e && (e.name || e.path || '')) || ''
          if (!name || !/\.md$/i.test(name)) continue
          let mtime = 0
          try {
            const info = await fs.stat(await fs.resolve('.scratch/handoff/' + name, { cwd: cwd }))
            if (info) {
              const mt = info.mtime
              mtime = typeof mt === 'number' ? mt : (mt ? Date.parse(String(mt)) : 0)
            }
          } catch (e2) { mtime = 0 }
          mds.push({ name: name, mtime: mtime })
        }
        mds.sort(function (a, b) { return b.mtime - a.mtime })
        return { ok: true, file: mds.length ? mds[0].name : null }
      } catch (e) {
        return { ok: true, file: null }  // 目录不存在/不可读 = 还没有交接文档
      }
    })

    // ============ 认领（开始此 Issue 流程 · T5 #347）============
    // 用户在 UI 点击「确认开始」且勾选认领后调用：gh issue edit <n> --add-assignee @me。
    // 写操作前 UI 已二次确认（用户点击即同意），不走 approval 服务（RESEARCH-NOTES §3 结论）。
    harness.handle('wf.claim', async function (args) {
      const n = args && args.number
      const cwd = (args && args.cwd) || DEFAULT_CWD
      if (!n) return { ok: false, error: '缺少参数 number（ticket 号）' }
      const repo = await getRepoKey(cwd)
      if (!repo) return { ok: false, error: { kind: 'env', error: '无法解析 owner/repo（git remote 或 gh repo view 失败）' } }
      const r = await runGh(['issue', 'edit', String(n), '--add-assignee', '@me'], cwd)
      if (!r.ok) return { ok: false, error: r }
      // 认领成功 → 取当前用户 login 供面板展示；失效快照缓存，让下次 wf.snapshot 拉到新 assignee
      let assignedTo = ''
      const u = await runGh(['api', 'user', '-q', '.login'])
      if (u.ok) assignedTo = u.text.trim()
      cache = { ts: 0, snapshot: null, error: null }
      return { ok: true, number: n, assignedTo: assignedTo, url: 'https://github.com/' + repo.owner + '/' + repo.name + '/issues/' + String(n) }
    })

    // ============ 轮询：已按 #348 拍板 Q3 关闭（60s 全量 × 8 map ≈ 2400-4800 GraphQL points/h 贴 5000 限额）============
    // 刷新策略 = 纯手动（状态条/面板按钮 wf.refresh）+ 打开面板即刷（client 侧 loadSnapshot）。
    // P1 若做状态变化 toast 提醒，再考虑低频自动（届时恢复本块并观察配额）。
  },
}
