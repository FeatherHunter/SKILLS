---
name: MuseSparkInit
description: 让 Muse Spark 1.2 在 DSH 可用并绕开中国地区限制。触发词：初始化 Muse Spark/配置 Muse Spark 1.2/MuseSparkInit/修复 Muse Spark 403/让 Muse Spark 可用
---

# MuseSparkInit

## 什么时候用

- 用户要初始化 `muse-spark-1.2-contributor` 到 DSH
- 用户报 `403 RegionError / API key is invalid / Model not supported` 且模型为 Muse Spark

## 需要什么

- `OPENCODE_GO_API_KEY`（`sk-...`，由用户提供，对应 `~/.dsh/.credentials.yaml`）
- 本机已安装的 Clash（或同类）代理，监听端口现场探测，不假设为 `7890`

## 步骤说明

### 步骤 1 — 读现状

1. 读 `~/.dsh/settings.yaml` 的 `llm-pi-ai.providers`，记录已有路由 id
2. 读 `~/.dsh/.credentials.yaml` 确认 `OPENCODE_GO_API_KEY` 是否存在
3. 读 `C:\Users\辰辰洋洋\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\verge.yaml` 的 `enable_tun_mode`

### 步骤 2 — 探测是否被地区限制

1. 不带代理 `POST https://opencode.ai/zen/go/v1/responses` body `{"model":"muse-spark-1.2-contributor","input":"hi","max_output_tokens":20}`
   - 返回 `403 RegionError` → 被限制
   - 返回 `200` → 未被限制，跳到步骤 3
   - 返回 `401 Model not supported` → 模型 id 已更名，按步骤 3 写入新 id
2. 探测本机代理地址：`Get-NetTCPConnection -State Listen` 找实际监听端口 + `HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings` 的 `ProxyServer/ProxyEnable` + `env:HTTP_PROXY`
3. 用探测到的代理地址重发同请求（`Invoke-RestMethod -Proxy http://<探测到的地址>`）
   - 返回 `200` → 代理可穿透
   - 仍 `403` → 代理不可用，提示用户切换 Clash 节点

### 步骤 3 — 写入配置

1. 备份 `~/.dsh/settings.yaml` 为 `settings.yaml.bak.<时间戳>`
2. 以探测到的路由 id（无冲突则用 `opencode-go-muse`）为锚，精确写入：

```yaml
llm-pi-ai:
  providers:
    <路由 id>:
      apiKeyEnv: OPENCODE_GO_API_KEY
      displayName: "Muse Spark Contributor"
      api: openai-responses
      baseURL: https://opencode.ai/zen/go/v1
      models:
        - id: muse-spark-1.2-contributor
          name: Muse Spark 1.2 Contributor
          input: [ text ]
          contextWindow: 1048576
          maxTokens: 13272
          reasoningEfforts:
            minimal: minimal
            low: low
            medium: medium
            high: high
            xhigh: xhigh
```

3. 校验：`node -e "yaml.parseDocument(...)"` 0 errors 且 `Config()` 返回 `Config OK`

### 步骤 4 — 配置代理穿透（仅当步骤 2 判定被限制时）

按以下优先级执行，成功一条即停：

**A. TUN 模式（首选，无需改代码）**
- 将 `verge.yaml` 的 `enable_tun_mode` 设为 `true`，重启 Clash Verge（需管理员创建 `Meta` 网卡），重启 DSH

**B. 系统代理 + 运行时补丁（TUN 不可用时）**
- 执行 `setx HTTP_PROXY http://<探测到的地址> / setx HTTPS_PROXY 同值 / setx ALL_PROXY 同值`
- 安装 `undici` 到三处：`C:\Users\辰辰洋洋\AppData\Roaming\DSH Desktop\agent`、`C:\Users\辰辰洋洋\.dsh\profiles`、`D:\0Tools\DSHDesktop\DSH Desktop\resources\app`
- 在三处的 `node_modules/@earendil-works/pi-ai/dist/api/openai-responses.js` 顶部加入 `import { ProxyAgent } from "undici"` 和 `import { resolveHttpProxyUrlForTarget } from "../utils/node-http-proxy.js"`，在 `createClient` 内加入通过 `resolveHttpProxyUrlForTarget(model.baseUrl)` 创建 `ProxyAgent` 并以 `dispatcher` 注入 `globalThis.fetch`
- 重启 DSH

### 步骤 5 — 验证

1. 选 `Muse Spark Contributor / muse-spark-1.2-contributor` 发 `hi`
2. 预期 `200` 且 `status=completed`，`reasoning_tokens` 正常

## 场景判断

| 场景 | 应该做 | 不应该做 |
|---|---|---|
| 直连 `200`，模型可通 | 只执行步骤 3 | 不执行步骤 4 |
| 直连 `403`，代理 `200` | 步骤 3 + 步骤 4 | 不重写整文件，不改 `agent-default-model`（除非用户要求设为默认） |
| 直连 `401 Model not supported` | 按步骤 3 写入新 id `muse-spark-1.2-contributor` | 不保留旧 `muse-spark-1.2` |
| 已被限制但本机无代理监听 | 提示用户启动 Clash / 切换节点 | 不硬编码 `7890` 也不静默失败 |
| `input: [text, image]` | 保持 `[text]` | 不声明 `image`（网关 `input_image` 返回 400） |
| `reasoningEfforts` 含 `max` | 只保留 5 档 `minimal/low/medium/high/xhigh` | 不写 `max/none/off:bare` |

## 其他约束

- `displayName` 必须加引号
- `baseURL` 必须为 `https://opencode.ai/zen/go/v1`，不含 `/responses`
- `maxTokens` 写入 `13272` 会成为请求默认值，符合该模型硬上限

## 回滚

- `settings.yaml.bak.<时间戳>` 覆盖
- 若改过 `verge.yaml:enable_tun_mode` 则改回原值
- 若打过补丁则用 `*.bak.*` 还原 `openai-responses.js` 并重启 DSH
