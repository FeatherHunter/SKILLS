# 01 — md color migration:AI 路由表 D8 同步(`color-grade` → `color`)

**What to build:**
`references/AI路由表-意图JSON字段枚举.md` 中残留 2 处 `color-grade`,与 D8 决策(段内调色 op 命名为 `color`,不带 `-grade` 后缀)矛盾。本工单把这两处同步为 `color`,让 AI 读路由表时看到的 op 命名与 HTML / JSON Schema 完全一致。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

### 验收标准

- [ ] 修改 `references/AI路由表-意图JSON字段枚举.md` 第 1 节字段枚举表:
  - 找到 `time_segments[].ops` 行的 `color-grade` 字样
  - 改为 `color`(不带后缀)
- [ ] 修改同一文件第 2 节 AI 路由表的段内 op 表:
  - 找到 `time_segments[j].ops.color-grade` 行
  - 改为 `videos[i].time_segments[j].ops.color`
  - 保留路由 CLI 描述 `video_color.py + trim`
- [ ] **不动**其他位置(避免破坏 spec 已知事实)
- [ ] 验证 `grep -n "color-grade" references/AI路由表-意图JSON字段枚举.md` 输出 0 行
- [ ] 验证 `grep -n "color" references/AI路由表-意图JSON字段枚举.md | grep -i "段内"` 显示 `color` 已就位
- [ ] 跑现有 `references/tests/test_intent_v3_schema.py` 全过(无回归)
- [ ] 跑现有 `智剪工坊-意图编辑-tests/test_html_v3_structure.py` 全过(无回归)

### 实现细节(供 agent 参考)

**修改 1** — 第 1 节字段枚举表 line 44:

原:
```
| `videos[i].time_segments[].ops` | 数组 | object | `mute` / `speed-up` / `slow-down` / `reverse` / `color-grade`(白名单) | 段内 op。**不在白名单 = 报错**(HTML `validateIntent` 拒绝) |
```

改:
```
| `videos[i].time_segments[].ops` | 数组 | object | `mute` / `speed-up` / `slow-down` / `reverse` / `color`(白名单) | 段内 op。**不在白名单 = 报错**(HTML `validateIntent` 拒绝) |
```

**修改 2** — 第 2 节 AI 路由表段内 op 表 line 92:

原:
```
| `videos[i].time_segments[j].ops.color-grade` | `video_color.py` + `trim` | `on=true` | `{on: bool, preset: str}` |
```

改:
```
| `videos[i].time_segments[j].ops.color` | `video_color.py` + `trim` | `on=true` | `{on: bool, preset: str}` |
```

### 已知事实(避免 agent 误判)

- **HTML `SEGMENT_OPS_SCHEMA.color` 不变**(已对齐 D8)
- **spec §7 `validSegmentOps` 不变**(已对齐 D8)
- **JSON Schema 白名单不变**(已对齐 D8)
- **`lib/video_processing.py` 不变**(读 `ops.color`,不读 op 名)
- **ADR 0007**(D8)已在本批 ticket 02 中沉淀,**本工单是 D8 决策的遗漏执行**

### 为什么这条 ticket 独立

即便 ticket 02(ADR 撰写)完成,AI 路由表本身需要同步改名才能生效。
本工单 = D8 决策的最后落地步骤。

如果跳过本工单:**AI 路由表仍写 `color-grade`,但 JSON 是 `color`,AI 路由失败** —— 是 bug。