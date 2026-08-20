# 坑位详档 · awesome-dsh-plugin-submit

> 高频 9 条 + 调试流程 + 报错速查表。所有案例均来自官方 `awesome-dsh-plugin/awesome-dsh-plugin/contributing.md` 与维护者 issue 跟踪的明示条款。

## 坑位 1 · 缺 `dsh.bundle` / 只声明 `dsh.client`

**现象**：CI 第一关 `dsh.bundle` 检查失败，PR 标 ❌，错误信息类似：

```
✗ dsh.bundle not declared in package.json
✗ only dsh.client found — plugin not installable
```

**根因**：`dsh.client` 只用于**前端 UI 注入**，**不能独立安装**。可安装的 DSH 插件必须有 `dsh.bundle`（通常是 `bundle.patch` 指向 `cordis.patch.yml`）。

**修复**：

```jsonc
// package.json
{
  "dsh": {
    "bundle": { "patch": "./cordis.patch.yml" },   // ← 必须
    "client": { "platform": "web" }                // 仅带前端 UI 时需要
  }
}
```

仓库根放 `cordis.patch.yml`：

```yaml
- insert:
    - id: 你的插件-id
      name: 你的包名
      config: {}
```

**预防**：用 `dev_scaffold_plugin`（DSH super injector 提供）生成插件骨架，自动带 `dsh.bundle`。

---

## 坑位 2 · 仓库创建 < 1 天

**现象**：CI 报错 `repo age < 1 day`。

**根因**：过去人工被迫拒掉的大多是"PR 前几分钟才建好"的仓——CI 自动卡。

**官方原话**："它不是对插件质量的评价。如果暂时没达标，把功能做完再提交即可，**重新提交不会有任何影响**。"

**修复**：等 1 天 + 把功能做完再提。

---

## 坑位 3 · 提交数 < 10

**现象**：CI 报错 `commit count < 10`。

**根因**：同坑位 2，防"占位仓"。

**官方原话**："重新提交不会有任何影响。" 不到 10 个 commit 就继续开发，每完成一个功能一次 commit，凑到 10 再开 PR。

---

## 坑位 4 · YAML 含未引号的 `: `

**现象**：

- CI YAML lint 报错 `mapping values are not allowed here`
- 或解析为嵌套键，导致 description 丢失

**根因**：YAML 把 `: `（冒号+空格）当**键值分隔符**。

**修复**：

```yaml
description:
  en: 'Vision toolkit: OCR, grounding and pixel diff.'   # ✅ 加单引号
  zh: '识图工具包：OCR、定位与像素比对。'                  # 中文全角冒号无此问题，但加也无妨
```

**中文全角冒号无此问题**——只有半角 `: ` 会触发。

---

## 坑位 5 · 分类选错

**现象**：PR 评论"建议改到 X 分类"，维护者**直接帮你改**，**不打回**。

**根因**：分类体系本身在演化（`usage` / `vision` / `security` / `browser` 等都是从 `tools` / `ui` / `dev` 拆出来的）。

**官方原话**："不会有人因为分类被打回——如果有更贴切的，维护者直接改。**挑最接近的一个即可，不必纠结**。"

**预防**：参考 §流程 3 分类速查表；不确定就选 `tools` 或 `ui`（最通用），维护者会改。

---

## 坑位 6 · `peerDependencies` 漏 prerelease 分支

**现象**：用户 `npm install` 时撞：

```
npm error ERESOLVE could not resolve
npm error While resolving: your-plugin@1.0.0
npm error Found: @deepseek-ai/dsh-tools@0.1.0-rc.6
```

**根因**：node-semver 只在范围里有**同一 `major.minor.patch` 元组且自身带 prerelease 标签**的比较符时，才放行 prerelease 版本。

```jsonc
// ❌ 看起来很宽，实际匹配不到 0.1.0-rc.6
"peerDependencies": { "@deepseek-ai/dsh-tools": ">=0.0.1-rc.1 <0.2.0" }

// ❌ "匹配一切"也不匹配 prerelease
"peerDependencies": { "@deepseek-ai/dsh-tools": ">=0.0.0-0 <0.2.0-0" }

// ✅ 在 0.1.0 元组上显式带 prerelease 标签
"peerDependencies": { "@deepseek-ai/dsh-tools": ">=0.0.1-rc.1 <0.1.0 || >=0.1.0-rc.1 <0.2.0-0" }
```

**官方原话**："漏了 → 用户 ERESOLVE，体验事故。"

**预防**：写 `peerDependencies` 时如果范围包含 prerelease（如 `0.1.0-rc.6`），必须用显式 `||` 分支。

---

## 坑位 7 · 截图用了第三方图床

**现象**：构建报错 `screenshot URL not on github.com host`。

**根因**：构建时校验——只允许 GitHub 托管的 https URL（`raw.githubusercontent.com` / `user-images.githubusercontent.com` / `camo.githubusercontent.com` / `github.com` attachments）。**第三方图床被拒是为用户隐私**——市场不会给用户一个无法担保来源的下载链接。

**修复**：

1. 把图片放自己仓库 `assets/` 目录
2. URL 用 `https://raw.githubusercontent.com/<owner>/<repo>/<branch>/assets/...`

**预防**：直接放自己仓库，跟着版本一起维护。

---

## 坑位 8 · 改了 README 没改 YAML

**现象**：下次维护者或自己跑 `node scripts/generate-readme.mjs` 时，你的修改被覆盖回原始状态。

**根因**：README 是脚本生成的。**禁止手工编辑 README**（`contributing.md` 反复强调）。

**修复**：

- 修改条目 → 改 `data/plugins/<owner>__<repo>.yml`
- 跑 `node scripts/generate-readme.mjs` 重生成
- 提交 YAML + 生成的 README 两个文件一起

---

## 坑位 9 · 改自己条目时顺手改了别人

**现象**：PR 改了 3 个条目的描述，但只有 1 个是"自己的"。维护者用 #1348 这种 issue 跟踪这种事故——曾两次蒙混过关，原因是"所有机械检查都通过了：YAML 合法、README 能生成、lint 干净"。

**根因**：手工编辑 README → 行号移位 → 改动落到邻居身上。

**官方原话**："现在 gate 会列出 PR 修改的每一个既有条目，以便被追问。"

**修复**：

- 用 `git status` 确认只 `add` 自己的 YAML 文件
- 重生成 README 后用 `git diff README.md` 自检：只应该有"新增 1 行"或"修改 1 行"，**不应该**有多行修改
- 如果发现 README 多行变了 → `git checkout README.md` 重新生成（用 `node scripts/generate-readme.mjs` 后只 add 自己 YAML + 重生成的 README）

---

## CI 报错速查表

| 报错信息 | 对应坑位 | 一句话修复 |
|---|---|---|
| `dsh.bundle not declared` | 坑位 1 | `package.json` 加 `dsh.bundle.patch`，仓库根放 `cordis.patch.yml` |
| `repo age < 1 day` | 坑位 2 | 等 1 天 |
| `commit count < 10` | 坑位 3 | 多 commit，凑到 10 再提 |
| `mapping values not allowed here` | 坑位 4 | 描述加单引号 |
| `category mismatch` | 坑位 5 | **不是错**——维护者会改，不必动 |
| (用户侧 `ERESOLVE`) | 坑位 6 | peer 范围加 `\|\| >=0.1.0-rc.1 <0.2.0-0` 分支 |
| `screenshot URL not on github.com` | 坑位 7 | 换 `raw.githubusercontent.com` |
| `README drift` | 坑位 8 | 改 YAML 不要改 README |
| `PR modifies N entries`（N > 1） | 坑位 9 | 只 add 自己的 YAML，README 重生成后只多/改 1 行 |

## 调试流程（PR 被打回时）

1. 看 PR 评论——维护者会**明确指出要改什么**
2. 改对应 YAML 文件
3. **同一分支直接 push**——不需要重开 PR，CI 自动重跑
4. 循环 1-3 直到 CI 全绿 + 维护者 approve
5. 合并后网站自动重建，无需做其它事

**官方原话**："反馈会以 PR 评论给出，明确指出要改什么。因描述不准确被打回不是对插件本身的否定——改好那一行即可收录。"