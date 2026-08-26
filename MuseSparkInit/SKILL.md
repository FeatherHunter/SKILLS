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
          name: muse-spark-1.2-contributor
          input: [ text, image ]
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
| `input: [text, image]` | 保持 `[text, image]`（多模态声明，不影响纯文本调用） | 不要剥成 `[text]`——升级后用户偏好即如此 |
| `reasoningEfforts` 含 `max` | 只保留 5 档 `minimal/low/medium/high/xhigh` | 不写 `max/none/off:bare` |

## 其他约束

- `displayName` 必须加引号
- `baseURL` 必须为 `https://opencode.ai/zen/go/v1`，**不带** `/responses` 路径段——`pi-ai` 直接把字段值传给 OpenAI SDK，OpenAI SDK 内部默认拼 `/responses`，所以 settings.yaml 里写 `/v1`、DSH 模型下拉显示的实际请求 URL 是 `/v1/responses`
- `name` 字段可以直接用 `id`（如 `name: muse-spark-1.2-contributor`）——DSH 模型下拉会同时展示 `displayName` 与 `name`，无需改成人类可读标题
- `maxTokens` 写入 `13272` 会成为请求默认值，符合该模型硬上限

## 回滚

- `settings.yaml.bak.<时间戳>` 覆盖
- 若改过 `verge.yaml:enable_tun_mode` 则改回原值
- 若打过补丁则用 `*.bak.*` 还原 `openai-responses.js` 并重启 DSH

---

## 实战参考（2026-08-25 · DSH 桌面版 2.0.2 · 真机排查录）

> 本次在 **DSH 桌面版（Electron app.asar 打包）** 上完整走通「直连 403 → 代理穿透 → 补丁落地」的排坑全过程。以下经验能显著缩短未来里程。

### 1. 探测「直连 vs 代理」必须先显式区分，否则会被系统代理骗

- **坑**：PowerShell 的 `Invoke-WebRequest / Invoke-RestMethod` 默认走 **IE 系统代理**（`HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings` 的 `ProxyEnable/ProxyServer`）。本机 Clash 开了系统代理 + `HTTP_PROXY=127.0.0.1:7890` 时，**“直连探测”其实是代理穿透** → 误判为“未限制” → 白折腾一轮。
- **正确做法（强制真直连）**：用 `[System.Net.HttpWebRequest]` 且 `$req.Proxy = $null`：

```powershell
$req = [System.Net.HttpWebRequest]::Create('https://opencode.ai/zen/go/v1/responses')
$req.Method = 'POST'; $req.ContentType = 'application/json'
$req.Proxy = $null   # 关键：强制无代理
$req.Headers.Add('Authorization', 'Bearer ' + $key)
$req.Timeout = 20000
```

- 结果判定：`403 RegionError` = 真被地区限制；`200` = 未限制。
- 反过来**验证代理可穿透**：同请求 `$req.Proxy = New-Object System.Net.WebProxy('http://127.0.0.1:7890')`，`200` 即代理可用。

### 2. DSH 桌面版实际加载的 pi-ai 在 `app.asar.unpacked`，不是 agent/node_modules

- **关键认知**：DSH 桌面版（`D:\0Tools\DSH Desktop\resources\app.asar` + `app.asar.unpacked`）的 agent/LLM 依赖打包在 **`resources\app.asar.unpacked\node_modules\@earendil-works\pi-ai\`**。Electron 对 unpacked 目录**优先于 asar 内同名文件**加载。
- `%APPDATA%\DSH Desktop\agent\node_modules\@earendil-works\pi-ai` 那份是**不会被加载的死副本**——在上面打补丁无效（本次踩坑：改了 3 轮才定位）。
- **定位真实加载路径的方法**：
  - `npx -y @electron/asar list app.asar | findstr pi-ai` 看 asar 内清单
  - `npx -y @electron/asar extract app.asar <outDir>` 整包解出可读文件（extract-file 对含中文用户名路径不稳）
  - 直接查 `resources\app.asar.unpacked\node_modules\@earendil-works\pi-ai\dist\api\openai-responses.js` 在不在、有没有补丁特征

### 3. 补丁打对位置的完整套路（B 方案增强版）

在对的文件（`...\app.asar.unpacked\node_modules\@earendil-works\pi-ai\dist\api\openai-responses.js`）上：

1. **备份**：`Copy-Item <file> <file>.bak -Force`
2. **头部加 import**（该文件原本可能没有 undici/resolver）：

```js
import { ProxyAgent, fetch as undiciFetch } from "undici";
import { resolveHttpProxyUrlForTarget } from "../utils/node-http-proxy.js";
```

3. **createClient 顶部加硬编码代理块（对本域强制，不依赖环境变量）**：

```js
const baseHost = String(model.baseUrl || '');
if (!globalThis.__dshOpenCodeProxyPatched && baseHost.includes('opencode.ai')) {
    globalThis.__dshOpenCodeProxyPatched = true;
    try {
        const proxyAgent = new ProxyAgent('http://127.0.0.1:7890'); // 用现场探测的端口
        globalThis.fetch = (input, init) => undiciFetch(input, { ...init, dispatcher: proxyAgent });
    } catch {}
}
```

4. **语法验证**：`node --check <file>` -> EXIT 0
5. **端到端验证**（依赖同目录 undici 可解析）：在 unpacked 目录放 `.tmp-e2e.mjs`，node 跑；从 `~/.dsh/.credentials.yaml` 读 key -> `undiciFetch(url, { dispatcher: proxyAgent })`，预期 HTTP 200
6. **重启 DSH 生效**（补丁在进程启动时加载，必须重启）

### 4. 为什么「setx 用户级代理」对 DSH 桌面版无效

- `setx HTTP_PROXY/HTTPS_PROXY/ALL_PROXY` 写用户级注册表，**只对之后启动的新进程生效**。
- Electron 桌面应用（DSH Desktop.exe）从 explorer/启动器拉起，**是否继承 setx 的 user-env 不确定**（本次实测：重启多次都未继承 -> 兜底的 process.env 探测代理路径一直为空）。
- 结论：**不要依赖环境变量方案**（对桌面版），直接走硬编码补丁；TUN 模式可作为备选但需管理员建 Meta 网卡（本次未采用）。

### 5. 其他经验

- **日志是实锤**：`%APPDATA%\DSH Desktop\logs\dsh-*.log` 的 `[llm-fallbacks]` 行会显示 `opencode-go-muse/... -> minimax-cn/... (reason=trigger-code)`——trigger-code 即 AUTH 类错误触发降级，是「模型不可用」的最早信号。
- **“API key is invalid” 的误报**：DSH/pi-ai 把 403 RegionError 归一化成 `API key is invalid` 类错误——**不要因为文案以为是 key 问题**，先做步骤 2 的强制直连探测区分 403/401。
- **reasoning 模型响应**：`output` 里是 `type: "reasoning"`（加密内容），`output_text` 可能为空，这是正常现象；看 `status: completed` + `usage` 计数即可判定成功。
- **不要一次改多处**：先确认唯一真实加载路径（unpacked），改对一处 + 重启验证，成功即止；改多份反而会互相掩盖。
