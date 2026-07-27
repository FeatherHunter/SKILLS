# P1-10 · prompt 尾部填入形式(总纲 07 §)

## 用户反馈
> 你会发现用户复制后还要删除并且修改。
> 我建议 prompt 改造成 尾部让用户输入的形式。
> 例如:XXXXXXXXX: 在冒号后面让用户输入。

## 设计

```
[自然语言意图]

请填入:
  - {字段1}: ___
  - {字段2}: ___
```

- 复制整段到 AI → 替换 ___ 部分即可,前缀完整不动
- prompt 不暴露 CLI/DB/Python 路径(继续遵守 07 §)
- 字段列表来自每个 scenario 的真实输入需求

## 示例对比

### 旧 (用户反馈改造前)
prompt: 请帮我查一下叫 [物品名] 的东西在哪里。
→ 用户复制后要:删除"叫 [物品名] 的" + 替换为 "白T恤",容易漏

### 新
我要查物品:

请填入:
  - 物品名: ___
→ 用户复制后:只把 ___ 换成白T恤,前缀完整

## 实施

1. scripts/refactor_prompts.py — 32 场景批量改造
2. references/scenarios.yaml — 32 个 prompt 全改造
3. tests/test_help_center.py — 加 tail-input 格式校验

## Playwright 13/13 + pytest 101/101 全过
