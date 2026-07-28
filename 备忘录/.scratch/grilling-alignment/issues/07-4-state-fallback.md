# 07 — 4 状态 fallback 端到端(wide refactor · 5 模板)

**Parent**: `00-memo-skill-v1.1.5-refactor-spec.md`

**What to build:**
用户调用 `memo_cli help` 或任意 HTML 渲染入口时,得到的 HTML 输出只支持 4 状态 fallback:`success` / `empty` / `missing_data` / `error`(从原 5 状态删除 `offline`)。所有 5 个 HTML 模板同步修改。具体行为:

- 数据齐全 → 显示 `success` 分支(带结果数据)
- 无匹配结果 → 显示 `empty` 分支(空状态文案)
- 字段缺失 → 显示 `missing_data` 分支(部分数据提示)
- 异常抛出 → 显示 `error` 分支(错误信息 + 重试建议)
- 网络/服务离线 → **不再处理**(用户 R1 明确决策"不存在所谓离线的场景")

期间 `test_help.py` 新增 success 状态测试,守护模板的 success 分支正确触发。

**Blocked by:** ticket 03(`test_skill_structure.py` 是后续回归检测的入口之一,但本 ticket 独立可跑)

**Status:** ready-for-agent

## Acceptance criteria

- [ ] 5 个 HTML 模板的 fallback JS 都加 `success` 分支(目前只有 empty / missing_data / error)
- [ ] 5 个 HTML 模板的 fallback JS 都删 `offline` 分支
- [ ] `memo_render.py` 的 `_inject_body` 适配 4 状态 payload 注入
- [ ] `tests/test_help.py` 新增 ≥ 1 个 success 状态测试(总测试数 174 → 175+)
- [ ] 174+ pytest 全过
- [ ] `git grep "offline" -- 'templates/' 'script/'` 返回 0 行
- [ ] `git grep "success" -- 'templates/'` 返回 ≥ 5 行(每模板至少 1 个)

## Out of scope

- 5 状态回退(用户 R1 明确决策不保留)
- 模板设计语言/视觉(本 ticket 只改 JS fallback,不改 HTML 视觉)
- 跨 Skill 同步触发(本 ticket 0 跨 Skill 改动)
