// dsh-feishu-link · lib/ipc.mjs
// 主进程 ⇄ helper 子进程 stdio JSON-RPC 协议
//
// 协议规则：
// - 每条消息一行 JSON（以 '\n' 分隔）
// - 主进程 → helper：命令（cmd + payload + id 可选；id 用于关联异步响应）
// - helper → 主进程：事件（type + payload；同时支持对命令的响应 result/error）
// - helper 启动后立刻发送一条 `{type:'ready'}`（不带版本控制；DSH restart 重连靠此信号触发）
//
// IPC schema 完整定义（生产代码请严格遵守）：
//
// ─── helper → main（上行事件）───
//
// { type: 'ready' }                                                       — 子进程启动完成
// { type: 'botStarted', agentId, appId, domain }                            — WSS 已连接
// { type: 'botFailed', agentId, error: { kind, message } }                  — 连接失败，触发自动重启
// { type: 'botClosed', agentId, reason }                                    — WSS 正常断开
// { type: 'message', agentId, eventType, payload }                          — 收到 IM 消息（eventType 默认 'im.message.receive_v1'）
// { type: 'message_ack', agentId, messageId, ok, error? }                  — helper 主动回执（可选）
// { type: 'log', level, msg }                                               — helper 内部日志
//
// ─── main → helper（下行命令）───
//
// { cmd: 'startBot', payload: { agentId, appId, appSecret, domain } }      — 启动某 agent 的 WSS
// { cmd: 'stopBot',  payload: { agentId } }                                  — 停止某 agent 的 WSS
// { cmd: 'broadcastList', payload: [ { agentId, appId, appSecret, domain }, ... ] }  — 一次性喂所有 bot（helper 启动时使用）
// { cmd: 'shutdown' }                                                       — 优雅退出（SIGTERM 等价）
// { cmd: 'ping', id: 'xxx' }                                                — 健康探活；helper 回 `{result:'pong',id:'xxx'}`
//
// 关联性：
// - 命令若带 `id`，helper 必须以 `{result:'...' | error:'...', id}` 响应
// - 命令若不带 `id`，helper 不必响应（fire-and-forget）
//
// 错误传播：
// - 所有 error 流以 `{kind, message, raw?}` 形式，kind 与 lib/fetch.mjs 的 FeishuBindError.kind 对齐

/**
 * 写一行 JSON 到流（自动加 \n）
 */
export function writeLine(stream, obj) {
  if (!stream || !stream.writable) return false
  try {
    stream.write(JSON.stringify(obj) + '\n')
    return true
  } catch (_e) {
    return false
  }
}

/**
 * 从流里拼装完整 JSON 行（按 '\n' 切分，不完整行缓存到下个 chunk）
 *
 * @param {Buffer|string} chunk
 * @param {object} state - { buffer: '' }
 * @returns {Array<object>} 解析出的完整 JSON 对象列表
 */
export function parseLines(chunk, state) {
  if (!state || typeof state.buffer !== 'string') state = { buffer: '' }
  state.buffer += typeof chunk === 'string' ? chunk : chunk.toString('utf8')
  const lines = state.buffer.split('\n')
  state.buffer = lines.pop()  // 最后一项可能不完整
  const out = []
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line) continue
    try {
      out.push(JSON.parse(line))
    } catch (_e) {
      // 跳过坏行，避免阻塞下游
    }
  }
  return out
}

/**
 * 主进程侧的子进程封装（DSH `subprocess` 服务接口适配）
 *
 * @param {object} svc - DSH `subprocess` 服务实例
 * @param {string} nodePath - Node 可执行路径（main `subprocess.resolveExecutable('node')`）
 * @param {string} helperPath - helper.mjs 绝对路径
 * @param {object} [opts]
 * @returns {{
 *   start(): Promise<void>,
 *   stop(): Promise<void>,
 *   send(cmd): void,
 *   onEvent(handler): () => void,
 *   onExit(handler): () => void,
 *   isAlive(): boolean,
 *   aliveHandle: any,    // DSH subprocess handle
 * }}
 */
export function createHelperProcess(svc, nodePath, helperPath, opts) {
  opts = opts || {}
  const TIMEOUT_MS = typeof opts.timeoutMs === 'number' ? opts.timeoutMs : 30000
  const STDOUT_MAX = typeof opts.stdoutMax === 'number' ? opts.stdoutMax : 1024 * 1024
  const STDERR_MAX = typeof opts.stderrMax === 'number' ? opts.stderrMax : 512 * 1024

  let handle = null
  let parseState = { buffer: '' }
  const eventHandlers = new Set()
  const exitHandlers = new Set()
  let alive = false
  let exitPromise = null

  function fireEvent(msg) {
    for (const h of eventHandlers) {
      try { h(msg) } catch (_e) { /* swallow */ }
    }
  }
  function fireExit(code, signal) {
    alive = false
    for (const h of exitHandlers) {
      try { h({ code, signal }) } catch (_e) { /* swallow */ }
    }
  }

  function start() {
    if (handle) return exitPromise
    exitPromise = new Promise(function (resolve) {
      let resolved = false
      function done(reason) { if (!resolved) { resolved = true; resolve(reason) } }

      handle = svc.spawn({
        argv: [nodePath, helperPath],
        cwd: opts.cwd,
        stdio: {
          stdin: 'pipe',
          stdout: { maxBytes: STDOUT_MAX },
          stderr: { maxBytes: STDERR_MAX },
        },
        graceMs: 2000,
      })

      // stdout 解析
      if (handle.collected && handle.collected.stdout) {
        handle.collected.stdout.on('data', function (chunk) {
          const msgs = parseLines(chunk, parseState)
          for (let i = 0; i < msgs.length; i++) fireEvent(msgs[i])
        })
        handle.collected.stdout.on('end', function () {
          // 处理剩余 buffer（极少见）
          if (parseState.buffer) {
            try { fireEvent(JSON.parse(parseState.buffer)) } catch (_) {}
            parseState.buffer = ''
          }
        })
      }
      // 收集 stderr 为日志
      if (handle.collected && handle.collected.stderr) {
        handle.collected.stderr.on('data', function (_chunk) { /* 静默或转日志 */ })
      }

      handle.done.then(function (outcome) {
        fireExit(outcome.exitCode, outcome.signal)
        done('exit')
      }).catch(function (e) {
        fireExit(-1, 'spawn_error')
        done('spawn_error')
      })

      alive = true
      // 30s 内没收到 ready 就报警（但不一定终止）
    })
    return exitPromise
  }

  function stop(graceMs) {
    if (!handle) return Promise.resolve('not_started')
    try {
      writeLine(handle.stdin, { cmd: 'shutdown' })
      if (typeof graceMs === 'number' && graceMs > 0) {
        const killTimer = setTimeout(function () {
          try { handle && handle.terminate && handle.terminate() } catch (_) {}
        }, graceMs)
        // best-effort；exit 时清不清都行
      }
    } catch (_e) {
      try { handle && handle.terminate && handle.terminate() } catch (_) {}
    }
    return exitPromise || Promise.resolve('not_started')
  }

  function send(cmdObj) {
    if (!handle) return false
    return writeLine(handle.stdin, cmdObj)
  }

  function onEvent(handler) {
    eventHandlers.add(handler)
    return function () { eventHandlers.delete(handler) }
  }
  function onExit(handler) {
    exitHandlers.add(handler)
    return function () { exitHandlers.delete(handler) }
  }
  function isAlive() { return alive }

  return {
    start, stop, send, onEvent, onExit, isAlive,
    get handle() { return handle },
  }
}

/**
 * helper 子进程侧的 stdin 读取器（基于 readline，但兼容多种 stdio 流）
 *
 * @param {Readable} stdin - Node `process.stdin` 或类似流
 * @param {function} cmdHandler - 每条解析出的 cmd 对象
 */
export function createHelperCommandReader(stdin, cmdHandler) {
  // 避免引入 node:readline（有些 DSH spawn stdio 不能用 readline，用纯 data 监听更稳）
  let buf = ''
  stdin.on('data', function (chunk) {
    buf += chunk.toString('utf8')
    const lines = buf.split('\n')
    buf = lines.pop()
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue
      try {
        const obj = JSON.parse(line)
        cmdHandler(obj)
      } catch (_e) {
        // 坏行忽略
      }
    }
  })
  stdin.on('end', function () {
    if (buf) { try { cmdHandler(JSON.parse(buf)) } catch (_) {} buf = '' }
  })
}
