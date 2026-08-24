# package.json 发布清单（通用）

> 任何 npm 包发布前的最小检查项。框架/平台的额外字段（如插件 manifest）仅在对应生态下需要，不进入通用必查路径。

## 通用骨架

```json
{
  "name": "my-package",
  "version": "1.0.0",
  "description": "一句话说明（npm 页面展示）",
  "license": "MIT",
  "type": "module",
  "main": "dist/index.js",
  "exports": {
    ".": "./dist/index.js",
    "./package.json": "./package.json"
  },
  "files": ["dist"],
  "keywords": ["keyword1", "keyword2"]
}
```

作用域包：`"name": "@scope/my-package"`。

## 字段检查表

| 字段 | 是否必查 | 说明 |
|---|---|---|
| `name` | 必查 | 全网唯一；小写 + 连字符；`npm view <name>` 404 才可用 |
| `version` | 必查 | 语义化 `x.y.z`，只增不减；同名同版本不可覆盖 |
| `description` | 必查 | npm 搜索与页面展示 |
| `license` | 必查 | 如 `MIT` / `Apache-2.0` |
| `files` | 必查 | 白名单，只含构建产物（如 `["dist"]` / `["lib"]`）；不含测试/文档/密钥 |
| `private` | 必查 | 必须不是 `true`，否则禁止发布 |
| `main` / `exports` / `bin` / `types` | 按需 | 与实际产物路径一致；`exports` 需包含 `"./package.json"` |
| `repository` / `homepage` / `bugs` | 建议 | 提升可信度 |
| `keywords` | 建议 | 提升搜索可见性 |
| `engines` | 按需 | 如 `"node": ">=18"` |

## `files` 白名单心法

- 能少则少：包里少一个文件比多一个安全
- 典型值：`["dist"]` 或 `["lib"]` 或 `["dist","README.md","LICENSE"]`
- 永远不进包：`node_modules`、`.env`、`.npmrc`、`.git`、测试、源码 `src`（除非你就是发源码）、内部文档

发布前必跑 `npm pack --dry-run` 核对 `Tarball Contents`，见 `pitfalls.md` 坑 5。

## 框架特定字段（可选附录）

如果目标平台要求额外 manifest（如某插件框架的 `myPlatform.client`、VS Code 的 `contributes`、CLI 的 `bin` 映射等），将其视为**框架附录**：

1. 在本清单之外单独维护一份 `<框架>-manifest.md`
2. 主流程不强制检查该字段，仅在"发布该框架插件"时才查
3. 不要让框架字段污染通用模板——通用包应保持零框架依赖

示例（仅示意，不作为通用必查）：

```json
{
  "myPlatform": { "client": { "platform": "web" } },
  "exports": { "./client": "./lib/client.js" }
}
```

> 上例仅说明"框架扩展"的存在形式，通用发布请忽略。
