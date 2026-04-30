# 通过 OpenClaw CLI 发送微信消息

通过 OpenClaw 手动发送微信消息的准确方法。

## 重要说明

⚠️ 这个 skill 记录的是 **openclaw-weixin 通道** 的发送方式，但师傅现在用的是 **Hermes 微信通道**（`openclaw-weixin` 是另一个独立插件，发的消息师傅收不到）。

**师傅现在聊天的通道是 Hermes**，该通道下消息是自动接收的，不需要也不支持手动 send 命令。文件发送需要走 Hermes gateway 的 REST API。

> 参考 `hermes-wechat-file-send-debug` skill 了解更多。

## 发送命令
```bash
openclaw message send -t "o9cq800qY4J0M3CqJY7hI40PXKt0@im.wechat" -m "打卡了吗？别忘了哦" --channel openclaw-weixin
```

## 常见错误

| 错误 | 原因 |
|------|------|
| `Unknown channel: weixin` | 用了错误的 channel 名，应用 `openclaw-weixin` |
| `Unknown channel: wx` | 同上 |
| `required option '-t, --target <dest>' not specified` | 忘记加 `-t` 参数 |

## 验证
发送成功会返回：
```
✅ Sent via openclaw-weixin. Message ID: openclaw-weixin:<timestamp>-<hash>
```
