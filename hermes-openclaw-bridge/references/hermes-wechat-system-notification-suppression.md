# 屏蔽微信系统通知

## 问题

当 Hermes 的 cron 任务运行时，如果你在微信发消息，会收到：

```
⚡ Interrupting current task (iteration 1/90). I'll respond to your message shortly.
```

这是 Gateway 在处理打断时自动发的 busy_ack，不是 cron 本身的输出。

## 解决方案

在 `config.yaml` 加入 per-platform 配置：

```yaml
platforms:
  weixin:
    suppress_busy_ack: true
```

在 `gateway/run.py` 第 1521 行附近插入平台检查：

```python
# Check if this platform suppresses busy_ack system notifications (e.g. WeChat)
platform_cfg = self.config.platforms.get(adapter.platform)
if platform_cfg and platform_cfg.get("suppress_busy_ack"):
    return True  # silently skip the "⚡ Interrupting..." ack, still process the interrupt
```

## 验证

重启 Hermes Gateway：
```bash
pm2 restart hermes-gateway
```

## 扩展

想屏蔽其他平台，只需在其他 platform 下加 `suppress_busy_ack: true`，例如：
```yaml
platforms:
  weixin:
    suppress_busy_ack: true
  telegram:
    suppress_busy_ack: true  # 电报也不发系统通知
```
