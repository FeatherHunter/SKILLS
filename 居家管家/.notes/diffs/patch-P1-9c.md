# P1-9c · HELP 中心(总纲 07 §)

## 文件
- `references/scenarios.yaml` — 场景资产唯一事实源(34 场景 × 31 唤醒词)
- `scripts/help_center.py` — 渲染器(yaml → payload)
- `templates/help_center.html` — 4 段式 + 每场景独立复制按钮 + clip 降级
- `scripts/home_manager/home_manager.py` — `help` 子命令

## 7 字段契约(总纲 07 §2.2)
每场景含: wake_word / scenario_id / scenario_title / dimensions / prompt / status / result

## 总纲 07 §核心规则
- 1. ✅ 登记 HELP 唤醒词 `居家管家 帮助`
- 2. ✅ HELP 不展示自身(查 '居家管家 帮助' 在 HTML 内只作为 wake_word 字段,不在 menu/header 中凸显)
- 3. ✅ HELP 命中走 HTML(invoke help_center.html)
- 4. ✅ 场景穷举(34 个场景,7 字段全填)
- 5. ✅ 场景资产唯一事实源(scenarios.yaml)
- 6. ✅ prompt 抽象(无 CLI / DB / Python 路径)
- 7. ✅ 二态 status(全部为空,可用)
- 8. N/A(无 【待开发】场景)
- 9. ✅ HTML 完整交付(31 groups + 34 scenarios 渲染)
- 10. ⚠️ 大规模可用(34 场景中等规模,折叠已实现)
- 11. ✅ 每场景独立复制按钮 + 复制反馈
- 12. ✅ 5 者一一对应

## 实现细节
- HTML JS 从 `<script id="payload">` 读 JSON(而非 `window.__DATA__`)
  → 与其他 9 个模板兼容(renderer 已就绪,本模板改读 JSON 模式)
- 复制按钮用 addEventListener 绑事件(避免 inline 引号转义)
- 复制成功 toast: `已复制 ✓` 1.5s
- 剪贴板降级: `navigator.clipboard.writeText` + `document.execCommand` 双通道
- 折叠/展开: 点击 group-h toggle `.open` class

## 验证
- `python3 scripts/home_manager.py help --output /tmp/x.html` → JSON 解析成功
  groups=31, scenarios=34
- pytest 71+27=98 全过
- Chrome 打开实际看:标题"居家管家 · 能力速查",31 个 group,34 个场景

## 风险
- yaml 中的 `[xxx]` / `,` 等会被 parser 误判 → 用引号包裹 string
- HELP HTML 在窄宽屏的体验未实测(总纲 04 §3 段式要求,留 P2 验证)