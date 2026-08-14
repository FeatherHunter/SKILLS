# dsh-waystation

> DSH（DeepSeek Harness）Web 界面的 **Waystation 控制面板**插件（Client + Host 双端），
> **配合 [Matt Pocock skills](https://github.com/mattpocock/skills) 的 wayfinder / triage / grilling / handoff 等技能使用**：
> 输入区状态栏胶囊（可接/占用/沉淀/交接/环境/更新）+ 自由悬浮面板（列表 / 技能 / 环境检查三视图）
> + GitHub issue 动作注入（诊断 / 修复 / 讨论 / 执行，均带 `/wayfinder` `/triage` 技能命令）
> + 交接开新会话。

- **插件包名**: `dsh-waystation`（可分发 npm 包，见 `package/`，当前 v1.0.1）
- **动态版 pluginId**: `wfst-1`（v9–v24 迭代产物）
- **平台**: Client（浏览器页面）+ Host（Node 进程，gh CLI 数据层）
- **配套**: [mattpocock/skills](https://github.com/mattpocock/skills)（wayfinder / triage / grilling / handoff / ask-matt 等）
- **两种形态**: ① 动态插件（进程内，会话级）；② 正式安装的本地插件（开机自启，推荐）

## 功能

| 模块 | 说明 |
|---|---|
| 状态栏胶囊 | 输入区上方：可接 / 占用 / 沉淀（零丢失快照）/ 交接 / 环境 / 更新，点击直达对应面板视图 |
| 面板 · 列表 | GitHub issue 全列表（map 置顶 + 子票进度条）、标签过滤 chips（GitHub 配置色）、被阻塞标签、已关闭折叠、行级动作按钮 |
| 面板 · 技能 | 技能雷达（推荐 / 列表 / 圆环），点击注入 `/skill` |
| 面板 · 环境检查 | 8 项前置检查（仓库定位 / setup / tracker / gh CLI / 登录 / API / 技能探测），红黄绿分组 + 一键处理 |
| 行级动作 | 按 label 四选一：诊断(`/triage`) / 修复(`/wayfinder`) / 讨论(`/wayfinder`) / 执行(`/wayfinder`)，按钮色 = GitHub label 配置色，点击预填输入框 |
| map 详情 | 顶部「执行」+ 任务按状态动作、可接/已认领/被阻塞/已关闭垂直走廊、Decision/Fog/Out-of-scope 折叠 |
| 交接 | 第一击注入 `/handoff` 时间戳模板；第二击预填 `/read` + 复述确认 prompt 并开新会话 |
| 统一引导句 | 动作注入统一带「从第一性原理出发完成任务，并对抗式审查。」 |

## 使用方式

### 方式一：正式安装（推荐 · 一条命令 · 开机自启 · 无需审批）

**一条命令完成全部**（装包 + 自动注册到 DSH profile，postinstall 自动写 `cordis.patch.yml`）：

```powershell
npm install --prefix "$env:USERPROFILE\.dsh\profiles" dsh-waystation --registry=https://registry.npmjs.org
```

- 装到 `~/.dsh/profiles/node_modules/dsh-waystation/`
- **postinstall 自动注册**：探测 DSH profile 的 `cordis.patch.yml`，若尚无 dsh-waystation 注册行则自动追加
  （幂等：重复安装/升级不叠加；非 DSH 环境自动跳过，不影响普通项目使用）
- 然后**刷新浏览器页面**即生效（无需重启 DSH、无需审批），之后每次 DSH 启动自动加载

卸载：

```powershell
npm uninstall --prefix "$env:USERPROFILE\.dsh\profiles" dsh-waystation
# 并手动删除 cordis.patch.yml 里的 dsh-waystation insert 块（或保留，DSH 找不到包会忽略）
```

> 原理：DSH 的 `dsh.client` 插件机制（`dsh-client-modules`）会扫描组合里声明了
> `dsh.client: { platform: 'web' }` 的包，把 `exports["./client"]` 指向的 bundle
> 伺服为 `/plugins/<id>/client.js` 并注入 `window.__DSH_BOOT__`，浏览器内核在启动
> 时自动挂载该插件条目。宿主半 `lib/index.js` 通过 `ctx.connection.rpc` 注册
> `/dsws` RPC 通道（gh CLI 数据层），Client 半经同一通道取数。

### 方式二：动态加载（零安装 · 会话级 · 重启失效）

在 DSH 会话中由 Agent 通过 Cordis 工具链加载：

1. `cordis_define` —— plugin 用 `kind: new`、`idPrefix: wfst`，code.host 填入
   [host.js](./host.js) 的内容、code.client 填入 [client.js](./client.js) 的内容。
2. `cordis_run` —— 首次运行需在界面批准（安全机制，Client 代码要在页面执行）。
3. 生效后输入区出现 Waystation 胶囊；Run 卡片内出现控制面板。

## 数据层说明（宿主半）

- 依赖：`gh` CLI（兜底路径 `D:\0Tools\GitHubCLI\gh.exe`）+ git 仓库工作目录（默认
  `D:\2Study\StudyNotes\SKILLS`，可随会话 cwd 切换）。
- 数据流：`gh issue list` 枚举 `wayfinder:map` → 每 map 一次 GraphQL（subIssues +
  labels + assignees + blockedBy）→ 组装快照（map 五区块解析 + tickets + stats）。
- RPC 通道 `/dsws`：`status` / `snapshot` / `refresh` / `cwd` / `handoffLatest` / `claim`。
- 刷新策略：纯手动（状态栏「更新」/ 列表「刷新」/ 打开面板即刷）+ 5s 快照缓存、
  30s 环境检查缓存。

## 文件

- `host.js` / `client.js` —— 动态版源码（cordis_define 的 `code.host` / `code.client` 函数体）
- `package/` —— **可分发插件包**（正式安装用，标准 npm 包结构）
  - `package.json` —— 包声明：`dsh.client`（platform web / immediately）
  - `lib/index.js` —— 宿主半（ESM：gh 数据层 + `/dsws` RPC 通道注册）
  - `lib/client.js` —— 浏览器半 bundle（`window.__ModuleLoader__.load` 注册格式）
- `README.md` —— 本说明
- `issues-checklist.html` —— 迭代需求清单（v9–v24，43+ 项）
- `DESIGN.md` / `prototype.html` —— 设计定稿与原型
- `tests/` —— host 逻辑测试（verify-status / verify-panel）

## 备注

- 若动态版（方式二）与正式安装版同时生效，两套 UI 会同时出现（同名插槽注册），
  建议保留正式安装版即可，动态版 `cordis_stop` 掉。
- 本插件需要 GitHub 仓库工作目录（wayfinder 地图仓库）才能取到数据；
  非仓库目录下环境检查会提示「仓库定位」未就绪。
- 用户界面偏好（开始模板等）存浏览器 localStorage，与动态版共用同一 key。
