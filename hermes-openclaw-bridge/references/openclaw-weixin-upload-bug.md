# openclaw-weixin 文件上传 Bug

## 错误信息
```
uploadFileAttachmentToWeixin: getUploadUrl returned no upload URL
```

## 根因

**iLink API v2.1+ 变更了响应格式**，openclaw-weixin 插件未适配。

| | 文档期望 | 实际返回 |
|---|---|---|
| 字段 | `upload_param` | `upload_full_url` |
| 内容 | 加密参数字符串 | 完整 URL（含 encrypted_query_param 等）|

插件期望 `upload_param` 字段，但 API 改成了返回 `upload_full_url` 完整 URL，导致插件无法获取上传参数。

## 影响范围

- 插件版本：2.1.1
- OpenClaw 版本：2026.3.24+
- 影响功能：发送图片/语音/文件等多媒体附件

## 原始 Issue

- 仓库：`hao-ji-xing/openclaw-weixin`
- Issue #11：「v2.1.1 getUploadUrl returns upload_full_url instead of upload_param」
- 状态：**open**（未修复）

## 修复方案

从 `upload_full_url` 中提取 `encrypted_query_param` 参数即可，URL 格式：
```
https://novac2c.cdn.weixin.qq.com/c2c/upload?encrypted_query_param=xxx&filekey=xxx&taskid=xxx
```
需要改插件源码 `packages/openclaw-weixin/` 解析这个 URL。

## 临时替代方案

1. **降级插件** — 装 v2.0.x（需看 OpenClaw 版本兼容性）
2. **只发文字** — 附件发送暂不可用
3. **等官方修复** — Issue #11 开了但维护者还没合并修复
