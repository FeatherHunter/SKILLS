# Hermes 微信文件发送调试

## 背景

微信发文件走 CDN upload REST API（`getUploadUrl`），和普通聊天消息不同。聊天是 gateway 长连接，发文件是独立的 REST API 调用。

## 关键教训：两个独立的微信通道

| 通道 | 命令 | 账号 | 用途 |
|------|------|------|------|
| `openclaw-weixin` | `openclaw message send` | OpenClaw 独立插件账号 | 插件自己配的微信小号 |
| Hermes微信 | Hermes gateway 接入 | Hermes 配置的微信账号 | **师傅现在聊天的通道** |

**两者 token 独立、账号独立、session 独立。** `openclaw message send` 发的消息不会出现在 Hermes 通道的对话里。

> 教训（0427）：师傅在 Hermes 通道里聊天，但 `openclaw message send --channel openclaw-weixin` 发的是另一个微信账号，发"你好"师傅微信里收不到。文件发送测试必须走 Hermes 平台，不能走 openclaw CLI。

- **聊天能用 ≠ 文件发送正常**：聊天走 gateway 长连接（不调用 REST API），文件发送走 REST API（依赖有效 token）
- **session timeout 的实际表现**：
  - REST API（getUploadUrl、sendMessage）返回 `errcode:-14 session timeout`
  - 但 gateway 长连接（getUpdates）依然活着，所以能收消息
- **两个独立系统**：
  - OpenClaw 微信: `~/.openclaw/openclaw-weixin/accounts/`
  - Hermes 微信: `~/.hermes/weixin/accounts/`
  - token 不同，账号不同，session 独立

## 调试步骤

### 1. 测试 API 响应

直接调用 getUploadUrl API 确认错误类型：

```javascript
// Node.js 测试脚本
const https = require('https');
const crypto = require('crypto');
const fs = require('fs');

const config = JSON.parse(fs.readFileSync(
  '/home/feather/.hermes/weixin/accounts/fb1bffb3465f@im.bot.json', 'utf-8'
));
const token = config.token;

const body = JSON.stringify({
  filekey: crypto.randomBytes(16).toString('hex'),
  media_type: 3,
  to_user_id: config.user_id.replace('@im.wechat', ''),
  rawsize: 1000,
  rawfilemd5: crypto.createHash('md5').update(Buffer.alloc(1000)).digest('hex'),
  filesize: 1008,
  no_need_thumb: true,
  aeskey: crypto.randomBytes(16).toString('hex'),
});

const options = {
  hostname: 'ilinkai.weixin.qq.com',
  port: 443,
  path: '/ilink/bot/getuploadurl',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'iLink-App-Id': 'bot',
    'iLink-App-ClientVersion': '2.1.7',
    'Authorization': `Bearer ${token}`,
    'Content-Length': Buffer.byteLength(body),
  }
};

const req = https.request(options, (res) => {
  let data = '';
  res.on('data', c => data += c);
  res.on('end', () => console.log('Body:', data));
});
req.write(body);
req.end();
```

### 2. 两种错误类型

| 错误信息 | 含义 | 解决方案 |
|---------|------|---------|
| `{"errcode":-14,"errmsg":"session timeout"}` | REST API 的 session 过期 | 重新 `hermes gateway setup` |
| 返回了 `upload_full_url` 但代码期望 `upload_param` | iLink API v2.1+ 返回格式变化 | 可手动 patch 插件解析 `upload_full_url` |

### 3. 快速修复
```bash
# Hermes 微信重新登录（推荐）
hermes gateway setup

# OpenClaw 微信重新登录
openclaw channels login --channel openclaw-weixin
```

## 相关文件位置
- OpenClaw 插件路径：`~/.openclaw/extensions/.openclaw-install-stage-z0Fc96/`
- Hermes 适配器：`~/.hermes/hermes-agent/gateway/platforms/weixin.py`
- 调试日志：在 `upload.ts` 加 `console.log(JSON.stringify(uploadUrlResp))`
