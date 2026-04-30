# 微信语音发送能力：目前做不到

## 调查结论

通过检查 Hermes Agent + OpenClaw bridge 配置，**目前无法向微信渠道发送语音消息**。

## 实测结论（2026-04-24）

| 方式 | 状态 | 说明 |
|------|------|------|
| `openclaw message send --channel openclaw-weixin` 文字 | ✅ 可行 | 正确 channel 名称 |
| `openclaw message send --media` 语音附件 | ❌ 失败 | `getUploadUrl returned no upload URL` |
| `send_message` 发微信文字 | ❌ 超时 | gateway ws 模式问题 |
| `send_message` 发微信附件 | ❌ 失败 | 不支持附件 |
| text_to_speech 生成的音频文件 | ❌ 无法发送 | 无附件发送路径 |

## 根因分析

### 1. openclaw-weixin 插件不支持语音附件
```
$ openclaw message send --media /tmp/audio.mp3
Error: uploadFileAttachmentToWeixin: getUploadUrl returned no upload URL
```
微信网页版上传文件需要先从腾讯服务器获取上传URL，openclaw-weixin 插件未能拿到该URL。这是插件层 bug。

### 2. Hermes `send_message` 发微信超时
```
Weixin send failed: Timeout context manager should be inside a task
```
gateway ws 模式发微信有 bug，但接收是正常的（你发消息我能收到）。

### 3. 正确 channel 名称是 `openclaw-weixin`
```
$ openclaw message send --channel weixin ...      # ❌ Unknown channel
$ openclaw message send --channel openclaw-weixin ... # ✅ 成功
```

## 技术架构参考
```
Hermes Agent
    ↓ text_to_speech (TTS) → 可生成 mp3
    ↓ send_message (失败/gateway bug)
    ↓ openclaw message send --channel openclaw-weixin → 文字✅ 附件❌
OpenClaw webhook bridge (openclaw-weixin 插件)
    ↓ 文字消息 → WeChat ✅
    ↓ 附件/语音 → ❌ getUploadUrl 失败
微信 (Weixin)
```

## 如果要实现

需要修 openclaw-weixin 插件的 `uploadFileAttachmentToWeixin` 函数，正确获取微信上传URL。或者等 OpenClaw 官方更新。

## 调查时用的命令
```bash
# 查看支持的 message send 渠道
openclaw message send --help

# 查看 Hermes 的消息目标
send_message action=list

# 尝试发微信文字（成功✅）
openclaw message send \
  --channel openclaw-weixin \
  --account 45d92e8c85c0-im-bot \
  --target "o9cq800qY4J0M3CqJY7hI40PXKt0@im.wechat" \
  --message "测试"

# 尝试发微信语音附件（失败❌）
openclaw message send \
  --channel openclaw-weixin \
  --account 45d92e8c85c0-im-bot \
  --target "o9cq800qY4J0M3CqJY7hI40PXKt0@im.wechat" \
  --message "语音测试" \
  --media "/tmp/audio.mp3"

# 生成 TTS 音频（成功）
openclaw infer tts convert --text "你好" --output /tmp/test.mp3

# 查看 OpenClaw 配置
cat ~/.openclaw/openclaw.json

# 查看微信账号配置
cat ~/.openclaw/openclaw-weixin/accounts/45d92e8c85c0-im-bot.json
```
