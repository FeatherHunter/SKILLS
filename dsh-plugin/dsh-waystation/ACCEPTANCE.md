# DSH-Waystation · P0 验收清单（ACCEPTANCE）

> 用途：运行时验收清单。插件经多轮迭代（v9→v14）在带 cordis 工具的会话中加载并实操验收，
> 本文件按 **v14 实际形态** 回填勾选结果（2026-08-14）。
> host 逻辑层测试：`node dsh-plugin/dsh-waystation/tests/verify-status.js`（21/21 PASS）+ `node dsh-plugin/dsh-waystation/tests/verify-panel.js`（22/22 PASS）。
> 对应：map #342 Destination 验收段 + ticket #361（新会话增强，v12 起按用户拍板改为「复制 prompt」轻量交互）。

## 0. 前置

- [x] 在带 cordis 工具的会话中 `cordis_define` + `cordis_run` 加载 `dsh-plugin/dsh-waystation`（pluginId `wfst-1`，当前 package `pkg-14`）
- [x] 工作目录 = 本仓库（D:\2Study\StudyNotes\SKILLS）

## 1. 输入区状态条（定稿 1A 居中胶囊 · v14）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 1.1 | 查看输入区上方状态条 | 居中胶囊：Waystation + 环境 n/8 + 可接 N + 占用 N + 沉淀 + 交接 + 更新 MM-DD HH:MM | ☑ |
| 1.2 | 点「更新」 | 全面板刷新（环境检查 + 快照），**手动刷新时面板显示遮罩 + 转圈并禁点**；刷新成功静默、失败才 toast | ☑ |
| 1.3 | 失败/未就绪时环境数字 | 显示 `--/8` 红色（不兜假数据），**数字区固定两位数等宽**（min-width 5ch，`6/8 ↔ --/8 ↔ 98/99` 状态栏宽度不变） | ☑ |
| 1.4 | 点「环境」段 | 面板切到「环境检查」页 | ☑ |
| 1.5 | 点「沉淀」段 | 输入框注入「零丢失快照」prompt（确认后发送） | ☑ |
| 1.6 | 点「交接」段（第一击） | 输入框注入 `/handoff` 模板（要求写 `.scratch/handoff/latest.md`），文案变「交接给新会话」 | ☑ |
| 1.7 | 再点「交接」段（第二击） | **新开空白会话**（workspaces.startSession，非 fork 不复制旧上下文）+ 输入框预填 `/read .scratch/handoff/latest.md`（定向传递，普通新会话不加载） | ☑ |

## 2. 主面板（三视图 · v14）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 2.1 | 侧栏「Waystation」/点状态条 | 面板开合；可拖动（头部+空白区）；8 向缩放（min 340×240 / max 900×920）；默认位置左上（16,76） | ☑ |
| 2.2 | 列表页 KPI 行 | 可接 / 占用 / 已关闭 计数 + 刷新按钮 | ☑ |
| 2.3 | 标签过滤 chips | 动态统计（GitHub 配置色）；**「全部」恒清空过滤并保持选中**（反复点击不进入空过滤态）；**chips 边框 = label 色深一档** | ☑ |
| 2.4 | 行级动作 | **按 label 三选一**：needs-triage→分流(/triage+URL) / bug→开始修复(/wayfinder+URL) / 其余 open→开始执行(/wayfinder+URL+流程指令)，点击均**复制 prompt**；按钮为 80% 小尺寸 | ☑ |
| 2.5 | map 行 | **视觉突出**（紫色竖条+浅紫底+图标放大+标题加粗）；点击进详情；行上另有「开始执行」按钮 | ☑ |
| 2.6 | 已关闭 | 列表底部「已关闭 (N)」折叠行（默认收起，展开可见，无动作按钮） | ☑ |
| 2.7 | 窄屏（面板宽 <380px） | 行内双栏固定（左列截断/右列按钮组不换行），动作按钮折叠为纯图标 | ☑ |
| 2.8 | 地图详情 | Destination/Notes 常显；Decisions/战雾/Out of scope 折叠；可接/已认领/被阻塞常显 + 已关闭折叠（阻塞缩进） | ☑ |
| 2.9 | 技能页 | 列表/圆环 A/B 切换；中心=推荐、环绕=相关（实心已装）；点击注入 /skill | ☑ |
| 2.10 | 环境检查页 | 横幅 + 缺失/部分就绪/就绪 分组卡；失败不兜假数据（`--/8`）；8 项检测（7/8 双层探测判「已安装但未挂载」） | ☑ |
| 2.11 | 主题安全 | 主色按钮（分流/开始修复/开始执行）固定 `#c084fc` 底 + `#140a1e` 字，任何主题下可读（不依赖 alias 变量） | ☑ |

## 3. 开始此 Issue（#347 · v12 起轻量化拍板）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 3.1 | 行级动作按钮点击 | **直接复制** prompt 到剪贴板（不弹窗、不开新会话、不认领——v12 拍板，wf.claim 保留未用） | ☑ |
| 3.2 | 复制文本内容 | 含 `/wayfinder`（或 /triage）+ issue 链接 + 流程指令 + 「独立新会话执行」提醒 + 命名建议 | ☑ |
| 3.3 | 开始模板配置（Run 卡「开始模板」） | /wayfinder 前缀开关 + 自定义模板（{number}/{url}/{title} 占位符），localStorage 持久化 | ☑ |

## 4. 多工作目录 / 多会话（v13 + v14）

| # | 操作 | 预期 | 结果 |
|---|---|---|---|
| 4.1 | 切换 skills ↔ StudyNotes 会话 | 状态条/面板跟随会话变化：cwd 由 host `sessions.meta` 权威反查（wf.cwd），sessionId 变化重探测并主动重拉 | ☑ |
| 4.2 | StudyNotes 会话 | 面板显示 **FeatherHunter/StudyNotes 自己的 issues/maps**（v14 修复 fetchMaps/fetchIssues 未透传 cwd 的串仓库 bug；已实测该仓库 issues 可枚举） | ☑ |
| 4.3 | 非 GitHub 仓库目录 | 空态标灰（「非 GitHub 仓库」），不混显默认仓库数据 | ☑ |
| 4.4 | 多会话并发 | client store **按会话隔离**（cwd/快照/筛选/视图独立）；面板/侧栏/Run 卡跟随当前激活会话（useSessions.current） | ☑ |

## 5. 结论

```
PASS 数：全部（1.x / 2.x / 3.x / 4.x 验收项均按 v14 实现逐项确认）
FAIL 项：无
  现象：
  处理：
验收人：FeatherHunter（多轮实操评审 + 2026-08-14 全部执行批次验证）
日期：2026-08-14
```

---

> 关联：map #342（[实施 map · DSH-Waystation P0 落地](https://github.com/FeatherHunter/SKILLS/issues/342)）
> 测试：node dsh-plugin/dsh-waystation/tests/verify-status.js && node dsh-plugin/dsh-waystation/tests/verify-panel.js（host 逻辑层，可随时重跑）
