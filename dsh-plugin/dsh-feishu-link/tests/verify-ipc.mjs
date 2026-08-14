#!/usr/bin/env node
/**
 * dsh-feishu-link · lib/ipc.mjs 自检脚本
 *
 * 跑：node tests/verify-ipc.mjs
 *
 * 测 IPC schema 解析：
 *   - writeLine 正确写入 JSON + '\n'
 *   - parseLines 按 '\n' 分块完整行，跨 chunk 缓存不完整行
 *   - 完整 JSON 对象正常还原
 *   - 坏行（无效 JSON）静默跳过
 */

import { writeLine, parseLines } from '../lib/ipc.mjs'

let pass = 0, fail = 0
function assert(cond, msg) {
  if (cond) { pass++; console.log('  ✓ ' + msg) }
  else { fail++; console.error('  ✗ ' + msg) }
}

function mockStream() {
  const chunks = []
  return {
    write(s) { chunks.push(String(s)); return true },
    writable: true,
    get text() { return chunks.join('') },
  }
}

function run() {
  console.log('# lib/ipc.mjs 自检')
  console.log('---')

  // ========== 1. writeLine ==========
  console.log('\n[1] writeLine')
  {
    const s = mockStream()
    writeLine(s, { type: 'ready', ts: 12345 })
    assert(s.text.endsWith('\n'), 'writeLine 末尾加 \\n')
    assert(JSON.parse(s.text.trim()).type === 'ready', 'writeLine 可解析回原对象')
  }
  {
    const s = mockStream()
    writeLine(s, { cmd: 'startBot', payload: { agentId: 'foo' } })
    assert(/startBot/.test(s.text), 'writeLine 序列化 cmd')
    assert(/"agentId":"foo"/.test(s.text), 'writeLine payload 内容')
  }
  {
    const s = mockStream()
    const r = writeLine(null, { x: 1 })
    assert(r === false, 'stream 为 null 时 writeLine 返回 false（不抛错）')
  }

  // ========== 2. parseLines（buffer 行为）==========
  console.log('\n[2] parseLines')
  {
    // 完整 3 行
    const state = { buffer: '' }
    const out = parseLines('{"a":1}\n{"b":2}\n{"c":3}\n', state)
    assert(out.length === 3, '3 完整行解析出 3 对象')
    assert(out[0].a === 1 && out[1].b === 2 && out[2].c === 3, '顺序与字段一致')
    assert(state.buffer === '', '完整输入 buffer 清空')
  }
  {
    // 不完整行缓存
    const state = { buffer: '' }
    const out = parseLines('{"a":1}\n{"b":', state)
    assert(out.length === 1, '不完整行只解析 1 对象')
    assert(out[0].a === 1, '第一行解析正确')
    assert(state.buffer === '{"b":', '不完整部分缓存到 buffer')
  }
  {
    // 续接不完整行
    const state = { buffer: '{"b":' }
    const out = parseLines('"hello"}\n{"c":3}\n', state)
    assert(out.length === 2, '续接后解析出 2 完整对象')
    assert(out[0].b === 'hello', '续接后第一行 b 完整')
    assert(out[1].c === 3, '续接后第二行 c 完整')
    assert(state.buffer === '', '续接后 buffer 清空')
  }
  {
    // 空行跳过
    const state = { buffer: '' }
    const out = parseLines('\n\n{"a":1}\n\n\n{"b":2}\n', state)
    assert(out.length === 2, '空行不影响解析')
  }
  {
    // 坏行跳过（不抛错）
    const state = { buffer: '' }
    const out = parseLines('not json\n{"a":1}\nalso bad\n{"b":2}\n', state)
    assert(out.length === 2, '坏行被静默跳过，只解析有效 JSON')
    assert(out[0].a === 1, '坏行后有效行解析正确')
  }
  {
    // chunk 切到中途
    const state = { buffer: '' }
    const o1 = parseLines('{"a":', state)
    assert(o1.length === 0, '不完整 chunk 不出对象')
    assert(state.buffer === '{"a":', '缓存在 buffer')
    const o2 = parseLines('1}\n', state)
    assert(o2.length === 1, '续接 chunk 出 1 对象')
    assert(o2[0].a === 1, '续接对象字段正确')
  }
  {
    // 支持 Buffer 类型输入
    const state = { buffer: '' }
    const buf = Buffer.from('{"k":"v"}\n', 'utf8')
    const out = parseLines(buf, state)
    assert(out.length === 1, 'Buffer 输入解析正确')
    assert(out[0].k === 'v', 'Buffer 内容解码正确')
  }

  // ========== 3. IPC schema 校验（手动 schema 校验样板）==========
  console.log('\n[3] IPC schema 抽样（验证重要命令契约）')
  {
    // writeLine 一条完整主进程→helper 命令
    const s = mockStream()
    writeLine(s, { cmd: 'startBot', payload: { agentId: 'a1', appId: 'cli_X', appSecret: 'sec_X', domain: 'feishu' }, id: 'req-001' })
    const parsed = JSON.parse(s.text.trim())
    assert(parsed.cmd === 'startBot', 'cmd 字段')
    assert(parsed.payload.agentId === 'a1', 'payload.agentId')
    assert(parsed.id === 'req-001', 'id 用于关联响应')
  }
  {
    // writeLine 一条完整 helper→主进程 事件
    const s = mockStream()
    writeLine(s, { type: 'message', agentId: 'a1', eventType: 'im.message.receive_v1', payload: { messageId: 'm_1', text: 'hello' }, ts: 12345 })
    const parsed = JSON.parse(s.text.trim())
    assert(parsed.type === 'message', '上行事件 type')
    assert(parsed.payload.messageId === 'm_1', '上行事件 payload')
    assert(parsed.ts === 12345, '上行事件 ts')
  }
  {
    // pong 响应（命令有 id 时的回执）
    const s = mockStream()
    writeLine(s, { result: { pong: true }, id: 'req-001' })
    const parsed = JSON.parse(s.text.trim())
    assert(parsed.result && parsed.result.pong === true, '命令有 id 时回 result')
    assert(parsed.id === 'req-001', '回执带同 id')
  }

  console.log('\n---')
  console.log(pass + ' passed · ' + fail + ' failed')
  process.exit(fail === 0 ? 0 : 1)
}

run().catch(function (e) {
  console.error('unexpected:', e)
  process.exit(2)
})
