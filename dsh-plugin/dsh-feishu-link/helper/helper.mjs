#!/usr/bin/env node
/**
 * dsh-feishu-link · helper 子进程（WSS 长连接持有者）
 *
 * 由 host 主进程通过 DSH `subprocess` 服务 spawn 起来。
 * 自身职责：
 *   1. 维护每个 agent 一个 WSS 连接（@larksuiteoapi/node-sdk v1.73 WSClient + EventDispatcher）
 *   2. 收 IM 消息 → 路由到主进程（type:'message'）
 *   3. 心跳 + 健康上报
 *   4. 接收主进程命令：startBot / stopBot / broadcastList / shutdown / ping / listBots
 *
 * 与主进程通讯协议：见 lib/ipc.mjs IPC schema
 * 启动后第一件事：send({type:'ready', ...})
 *
 * 依赖：
 *   - `@larksuiteoapi/node-sdk` v1.73+（仅本 helper 用，主进程 host.js 不用）
 *   - 与 DSH 私域服务零耦合
 *
 * 关联调研：RESEARCH-t1-endpoints.md §2/§3
 */

import * as lark from '@larksuiteoapi/node-sdk'
import { EventEmitter } from 'events'
import { createHelperCommandReader, writeLine } from '../lib/ipc.mjs'

const stdout = process.stdout
const stdin = process.stdin

// ============ 内部状态 ============

/**
 * bots Map<agentId, BotRecord>
 * BotRecord = {
 *   agentId, appId, appSecret, domain,
 *   ws: WSClient,
 *   dispatcher: EventDispatcher,
 *   status: 'connecting' | 'connected' | 'failed' | 'stopped',
 *   lastHeartbeatAt: number,
 *   startedAt: number,
 *   reconnectAttempts: number,
 * }
 */
const bots = new Map()
const HEARTBEAT_MS = 30000
const HEARTBEAT_CHECK_MS = 15000
const MAX_RECONNECT = 5
let shuttingDown = false

// ============ IPC 工具 ============

function send(msg) {
  writeLine(stdout, msg)
}

function log(level, msg) {
  send({ type: 'log', level, msg, ts: Date.now() })
}

// ============ 业务：startBot / stopBot ============

async function startBot({ agentId, appId, appSecret, domain = 'feishu' }) {
  if (!agentId || !appId || !appSecret) {
    send({ type: 'botFailed', agentId, error: { kind: 'invalid_request', message: 'agentId/appId/appSecret 缺失' }, ts: Date.now() })
    return
  }
  // 已有 → 先停
  if (bots.has(agentId)) {
    log('info', `stopBot before restart: ${agentId}`)
    await stopBot({ agentId, reason: 'restart' })
  }

  const ws = new lark.WSClient({
    appId,
    appSecret,
    domain: domain === 'lark' ? lark.Domain.Lark : lark.Domain.Feishu,
  })

  const dispatcher = new lark.EventDispatcher({}).register({
    // 收到任何 IM 消息：上行到主进程
    'im.message.receive_v1': (data) => {
      send({
        type: 'message',
        agentId,
        eventType: 'im.message.receive_v1',
        payload: extractMinimalMessage(data),
        ts: Date.now(),
      })
    },
  })

  const record = {
    agentId,
    appId,
    domain,
    ws,
    dispatcher,
    status: 'connecting',
    lastHeartbeatAt: Date.now(),
    startedAt: Date.now(),
    reconnectAttempts: 0,
  }
  bots.set(agentId, record)

  try {
    await ws.start({ eventDispatcher: dispatcher })
    record.status = 'connected'
    record.lastHeartbeatAt = Date.now()
    send({ type: 'botStarted', agentId, appId, domain, ts: Date.now() })
    log('info', `bot connected: ${agentId}`)
  } catch (e) {
    record.status = 'failed'
    send({
      type: 'botFailed',
      agentId,
      error: { kind: 'ws_start_failed', message: String((e && e.message) || e) },
      ts: Date.now(),
    })
    log('error', `bot start failed ${agentId}: ${e && e.message || e}`)
  }
}

async function stopBot({ agentId, reason = 'manual' }) {
  const record = bots.get(agentId)
  if (!record) return
  bots.delete(agentId)
  record.status = 'stopped'
  try {
    if (record.ws && typeof record.ws.close === 'function') {
      await record.ws.close()
    }
  } catch (_e) { /* swallow */ }
  send({ type: 'botClosed', agentId, reason, ts: Date.now() })
  log('info', `bot closed: ${agentId} (reason=${reason})`)
}

// ============ 消息归一化（只保留主进程路由需要的字段） ============

function extractMinimalMessage(data) {
  if (!data || typeof data !== 'object') return { raw: data }
  const m = data.message || data
  const sender = m.sender || {}
  const chat = m.chat || data.chat || {}
  // content 通常是 JSON 字符串（卡片可能更复杂），主进程再解析
  let content = m.content
  if (typeof content === 'string') {
    try { content = JSON.parse(content) } catch (_) { /* keep as string */ }
  }
  return {
    messageId: m.message_id,
    chatId: chat.chat_id || m.chat_id,
    chatType: chat.chat_type,    // 'p2p' | 'group' | ...
    messageType: m.msg_type || m.message_type,
    content,
    senderId: (sender.sender_id && sender.sender_id.open_id) || sender.id,
    senderType: sender.sender_type, // 'user' | 'bot' | ...
    createTimeMs: Number(m.create_time) || Date.now(),
  }
}

// ============ 心跳 ============

setInterval(() => {
  if (shuttingDown) return
  const now = Date.now()
  for (const [agentId, record] of bots.entries()) {
    const age = now - (record.lastHeartbeatAt || 0)
    if (age > HEARTBEAT_MS && record.status === 'connected') {
      // 心跳超时 → 标记 stalled（让主进程决定怎么恢复）
      send({ type: 'botStalled', agentId, ageMs: age, ts: now })
    }
  }
}, HEARTBEAT_CHECK_MS)

// ============ IPC 命令处理 ============

const cmdBus = new EventEmitter()

cmdBus.on('cmd', async (cmd) => {
  if (!cmd || typeof cmd !== 'object') return
  const id = cmd.id
  let result, error
  try {
    if (cmd.cmd === 'startBot') {
      await startBot(cmd.payload || {})
      result = { ok: true }
    } else if (cmd.cmd === 'stopBot') {
      await stopBot(cmd.payload || {})
      result = { ok: true }
    } else if (cmd.cmd === 'broadcastList') {
      const list = Array.isArray(cmd.payload) ? cmd.payload : []
      const results = []
      for (const b of list) {
        try { await startBot(b); results.push({ agentId: b.agentId, ok: true }) }
        catch (e) { results.push({ agentId: b.agentId, ok: false, error: String((e && e.message) || e) }) }
      }
      result = { ok: true, results }
    } else if (cmd.cmd === 'shutdown') {
      shuttingDown = true
      const agentIds = Array.from(bots.keys())
      await Promise.all(agentIds.map(aid => stopBot({ agentId: aid, reason: 'shutdown' })))
      send({ type: 'shutdownAck', id, ts: Date.now() })
      setTimeout(() => process.exit(0), 200)
      return
    } else if (cmd.cmd === 'ping') {
      result = { pong: true, ts: Date.now() }
    } else if (cmd.cmd === 'listBots') {
      const list = Array.from(bots.values()).map((b) => ({
        agentId: b.agentId,
        status: b.status,
        domain: b.domain,
        lastHeartbeatAt: b.lastHeartbeatAt,
        startedAt: b.startedAt,
        reconnectAttempts: b.reconnectAttempts,
      }))
      result = { ok: true, bots: list }
    } else {
      error = { kind: 'unknown_cmd', message: `unknown cmd: ${cmd.cmd}` }
    }
  } catch (e) {
    error = { kind: 'internal', message: String((e && e.message) || e) }
  }
  // 命令有 id 时回响应（无 id 则 fire-and-forget）
  if (id !== undefined && id !== null) {
    send(error ? { error, id } : { result, id })
  }
})

// ============ 启动 ============

createHelperCommandReader(stdin, (cmd) => cmdBus.emit('cmd', cmd))

// SIGTERM 优雅退出（DSH 重启时给机会）
process.on('SIGTERM', () => {
  log('info', 'received SIGTERM, graceful shutdown')
  cmdBus.emit('cmd', { cmd: 'shutdown' })
})

// uncaught 错误记录到日志（不杀进程）
process.on('uncaughtException', (e) => log('error', `uncaughtException: ${e && e.message || e}\n${e && e.stack || ''}`))
process.on('unhandledRejection', (e) => log('error', `unhandledRejection: ${e && (e.message || e) || e}`))

// 启动就绪信号（主进程拿到后会调 broadcastList）
send({
  type: 'ready',
  version: '0.1.0',
  node: process.version,
  pid: process.pid,
  ts: Date.now(),
})
