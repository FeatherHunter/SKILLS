---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 03
Blocked-by: ["02"]
---

# Phase B · pytest + FAT 验证

## 任务

Phase A-1 + Phase A-3 实施完成后,跑完整验证套件确保行为正确。

## 验证项

1. **pytest baseline**
   - 跑 `pytest tests/ -v`
   - 必须全绿(11 个测试文件,已知 ~100+ 用例)
   - 重点验证:`test_naming.py` 命名合规正则覆盖 15 模板中文 command 名

2. **Fresh Agent 黑盒测试(FAT · 总纲 §05 协议)**
   - 选 5 个核心唤醒词 + 2-3 个变体
   - 每个唤醒词用 ≥ 3 个口语化 prompt 各测一次
   - 验证 AI 命中后 invoke 正确 CLI + 中文文件名生成
   - **重要**:失败改 SKILL.md,不改正

3. **HTML 输出物理验证**
   - 跑 `python scripts/help_render.py` 生成作息管家.html
   - 验证作息管家.html 与 schedule_html/help/作息管家_HELP_<TS>.html 内容一致(Phase A-3 落地后)
   - 验证 15 模板文件名都是中文(Phase A-1 完成后)

4. **git diff 审计**
   - 检查 SKILL.md 路径引用与实际生成一致(Phase A-1 完成后)
   - 验证 CHANGELOG.md 更新(记录 Phase A-3 / A-1)

## 验证清单(checklist)

- [ ] pytest 全绿
- [ ] FAT 5 个核心唤醒词 × 2-3 变体
- [ ] help_render.py 输出作息管家.html 正确
- [ ] 15 模板中文文件名正确生成
- [ ] SKILL.md 路径引用与生成一致
- [ ] CHANGELOG.md 更新

## 触发条件

满足所有 checklist → Phase B 完成 → 全部重构闭环。

## 预期 commit

```
[作息管家] Phase B · 验证完成 · pytest baseline + FAT 通过

文件清单:
~ CHANGELOG.md                    (新增 Phase A-3 / A-1 / B 条目)

行为变化: 无 · 验证记录
向后兼容: ✅

Tested-By: fresh-agent-v1
  - 唤醒词: 查作息 / 查日程 / 修正作息 / 商量计划 / 复盘
  - 人类 prompt: ≥ 3 个口语化 prompt,各唤醒词至少 1 个
  - 结果: pass
```