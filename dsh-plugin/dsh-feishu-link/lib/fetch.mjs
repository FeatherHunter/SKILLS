// dsh-feishu-link · lib/fetch.mjs
// 4 纯 fetch 函数，用于飞书官方设备流（无 DSH 私域依赖；可在 host process / spawn helper / Node 子进程通用复用）
// 思路借鉴 limingboGitHub/dsh-feishu-connect index.js L912-1008（L1 #388 sub-agent 调研核实）。
// 关联文档：https://open.feishu.cn/document/uYjL24iN/uYjN3QjL2YzN04iN2cDN

const FEISHU_BASE = 'https://accounts.feishu.cn'
const FEISHU_API_BASE = 'https://open.feishu.cn'
const FEISHU_LARK_BASE = 'https://open.larksuite.com' // 海外版

/**
 * 通过域名获取飞书 API 根（feishu / lark 切换）。
 * 飞书：open.feishu.cn / 飞书 PersonalAgent 端点 accounts.feishu.cn
 * 海外 Lark：open.larksuite.com / accounts.larksuite.com（验证后启用）
 */
function apiBase(domain = 'feishu') {
  return domain === 'lark' ? FEISHU_LARK_BASE : FEISHU_API_BASE
}

/**
 * 应用注册设备流 BEGIN（生成 QR 码 payload）
 *
 * @param {object} args
 * @param {'feishu'|'lark'} args.domain
 * @param {'client_secret'} [args.authMethod] - 默认 client_secret
 * @param {'open_id'} [args.requestUserInfo] - 默认 open_id
 * @param {string} args.source - 标识（区分调用者，用于飞书侧统计），如 'dsh-feishu-link'
 * @param {string} [args.archetype] - 固定 'PersonalAgent'，触发"扫码即建应用"流程
 * @returns {Promise<{ deviceCode: string, verificationUriComplete: string, expiresIn: number, interval: number }>}
 * @throws {FeishuBindError}
 */
export async function beginBind({
  domain = 'feishu',
  authMethod = 'client_secret',
  requestUserInfo = 'open_id',
  source,
  archetype = 'PersonalAgent',
}) {
  const form = new URLSearchParams({
    action: 'begin',
    auth_method: authMethod,
    request_user_info: requestUserInfo,
    source,
    archetype,
  })
  const res = await fetch(`${FEISHU_BASE}/oauth/v1/app/registration`, {
    method: 'POST',
    body: form,
  })
  const text = await res.text()
  let j
  try { j = JSON.parse(text) } catch { throw new FeishuBindError('parse_failed', `feishu begin: not JSON (status ${res.status}): ${text.slice(0, 200)}`) }
  if (!res.ok || j.code !== undefined) {
    throw new FeishuBindError(j.error || `http_${res.status}`, j.message || j.msg || `feishu begin failed: ${text.slice(0, 200)}`)
  }
  const data = j.data || {}
  if (!data.device_code || !data.verification_uri_complete) {
    throw new FeishuBindError('invalid_response', `missing device_code / verification_uri_complete: ${text.slice(0, 200)}`)
  }
  return {
    deviceCode: data.device_code,
    verificationUriComplete: data.verification_uri_complete,
    expiresIn: typeof data.expires_in === 'number' ? data.expires_in : 600,
    interval: typeof data.interval === 'number' ? data.interval : 5,
  }
}

/**
 * 应用注册设备流 POLL（轮询扫码状态）
 *
 * @param {object} args
 * @param {string} args.deviceCode - begin 阶段拿到的 device_code
 * @returns {Promise<
 *   | { status: 'pending' }
 *   | { status: 'success', appId: string, appSecret: string, operatorOpenId?: string, tenant?: string, raw?: any }
 *   | { status: 'slow_down' }
 * >}
 * @throws {FeishuBindError} 业务错误（如 invalid_grant）一律抛错，由调用方决定是否停止轮询
 */
export async function pollBind({ deviceCode }) {
  if (!deviceCode) throw new FeishuBindError('invalid_request', 'deviceCode is required')
  const form = new URLSearchParams({ action: 'poll', device_code: deviceCode })
  let res, text
  try {
    res = await fetch(`${FEISHU_BASE}/oauth/v1/app/registration`, {
      method: 'POST',
      body: form,
    })
    text = await res.text()
  } catch (e) {
    throw new FeishuBindError('network', `poll network error: ${e && e.message || e}`)
  }
  let j
  try { j = JSON.parse(text) } catch { throw new FeishuBindError('parse_failed', `feishu poll: not JSON (status ${res.status}): ${text.slice(0, 200)}`) }

  // pending 状态：飞书侧返回 custom error = "authorization_pending"
  if (j.error === 'authorization_pending' || j.code === 'authorization_pending') {
    return { status: 'pending' }
  }
  // slow_down：用户刚扫，飞书侧要求降低轮询频率
  if (j.error === 'slow_down' || j.code === 'slow_down') {
    return { status: 'slow_down' }
  }
  // 成功
  if (res.ok && (j.code === 0 || !j.code)) {
    const data = j.data || {}
    return {
      status: 'success',
      appId: data.client_id,
      appSecret: data.client_secret,
      operatorOpenId: data.user_info && data.user_info.open_id,
      tenant: data.tenant || 'feishu',
      raw: data,
    }
  }
  // 其他错误
  throw new FeishuBindError(j.error || `http_${res.status}`, j.message || j.msg || `feishu poll failed: ${text.slice(0, 200)}`)
}

/**
 * 应用注册设备流 INIT（探测当前域支持哪些 auth_method；保留作为前置探测）
 *
 * 通常 V2 不需要单独调用（begin 时已隐含）。仅在 UI 想更早展示「支持什么流程」时使用。
 *
 * @returns {Promise<{ supportedAuthMethods: string[] }>}
 */
export async function initBind({ source }) {
  const form = new URLSearchParams({ action: 'init', source })
  const res = await fetch(`${FEISHU_BASE}/oauth/v1/app/registration`, { method: 'POST', body: form })
  const text = await res.text()
  let j
  try { j = JSON.parse(text) } catch { throw new FeishuBindError('parse_failed', `feishu init: not JSON: ${text.slice(0, 200)}`) }
  if (!res.ok || (j.code !== undefined && j.code !== 0)) {
    throw new FeishuBindError(j.error || `http_${res.status}`, j.message || j.msg)
  }
  return {
    supportedAuthMethods: (j.data && j.data.supported_auth_methods) || ['client_secret'],
  }
}

/**
 * 获取 tenant_access_token（长期凭证）
 *
 * 与设备流无关；用于发消息（im_send）等 API 调用，access_token 2 小时过期，需定时 refresh。
 * WSClient 内部也会用此 token。
 *
 * @param {object} args
 * @param {string} args.appId
 * @param {string} args.appSecret
 * @param {'feishu'|'lark'} [args.domain]
 * @returns {Promise<{ accessToken: string, expiresAt: number, refreshExpiresAt: number }>}
 */
export async function getTenantAccessToken({ appId, appSecret, domain = 'feishu' }) {
  if (!appId || !appSecret) throw new FeishuBindError('invalid_request', 'appId + appSecret required')
  const base = apiBase(domain)
  const res = await fetch(`${base}/open-apis/auth/v3/tenant_access_token/internal`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ app_id: appId, app_secret: appSecret }),
  })
  const text = await res.text()
  let j
  try { j = JSON.parse(text) } catch { throw new FeishuBindError('parse_failed', `feishu token: not JSON: ${text.slice(0, 200)}`) }
  if (!res.ok || j.code !== 0) {
    throw new FeishuBindError(`token_${j.code || res.status}`, j.msg || `feishu token error: ${text.slice(0, 200)}`)
  }
  const now = Date.now()
  return {
    accessToken: j.tenant_access_token,
    expiresAt: now + (j.expire - 60) * 1000, // -60s buffer 防边界过期
    refreshExpiresAt: now + 2 * 60 * 60 * 1000, // 飞书建议 2h 内重试
  }
}

/**
 * 发送 IM 消息（纯文本 / 卡片 / 图片）
 *
 * @param {object} args
 * @param {string} args.accessToken
 * @param {string} args.receiveId - 群 chat_id 或用户 open_id
 * @param {'chat_id'|'open_id'|'email'} [args.receiveIdType]
 * @param {'text'|'post'|'interactive'|'image'} [args.msgType]
 * @param {object} args.content - msgType 对应内容对象（text: {text: '...'}）
 * @param {'feishu'|'lark'} [args.domain]
 * @returns {Promise<{ ok: boolean, messageId?: string, chatId?: string, error?: any }>}
 */
export async function sendImMessage({
  accessToken,
  receiveId,
  receiveIdType = 'chat_id',
  msgType = 'text',
  content,
  domain = 'feishu',
}) {
  if (!accessToken || !receiveId) throw new FeishuBindError('invalid_request', 'accessToken + receiveId required')
  const base = apiBase(domain)
  const res = await fetch(
    `${base}/open-apis/im/v1/messages?receive_id_type=${receiveIdType}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        receive_id: receiveId,
        msg_type: msgType,
        content: typeof content === 'string' ? content : JSON.stringify(content),
      }),
    }
  )
  const text = await res.text()
  let j
  try { j = JSON.parse(text) } catch { j = { code: -1, msg: 'parse_failed', raw: text } }
  if (!res.ok || (j.code !== undefined && j.code !== 0)) {
    return { ok: false, error: { code: j.code, msg: j.msg, raw: text.slice(0, 300) } }
  }
  return {
    ok: true,
    messageId: j.data && j.data.message_id,
    chatId: j.data && j.data.chat_id,
  }
}

/**
 * 自定义错误类型（用于上层 catch + 状态机判定）
 */
export class FeishuBindError extends Error {
  constructor(kind, message) {
    super(message)
    this.name = 'FeishuBindError'
    this.kind = kind   // 'network' | 'parse_failed' | 'authorization_pending' | 'invalid_request' | 'http_xxx' | 'token_xxx' 等
  }
}
