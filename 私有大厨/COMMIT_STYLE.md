# 私有大厨 · commit 信息格式规范(2026-07-28 制定)

## 背景

对照 SKILLS 仓库其他 SKILL(居家管家/卡路里/饼干记账/作息管家/备忘录)的 commit 风格,
发现私有大厨历史 33 个 commit 用 `[feat/fix/docs/test(私家大厨)]` 的 conventional commits 英文 type prefix,
**与 SKILLS 仓库主流不一致**(其他 SKILL 都用 `[skill中文名] 描述` 中文风格)。

## 新规则(未来 commit 必用)

### 格式

```
[私有大厨] 描述
```

- prefix: `[私有大厨]` **必填**(中文方括号)
- **无** `feat` / `fix` / `docs` / `test` / `chore` / `refactor` 等英文 type prefix
- 描述: 中文为主,英文术语可接受(如 `argparse` / `JSON`)
- 可选标号: `Phase X.Y` 或 `vX.Y.Z` 放描述开头

### 范例(对比)

❌ 之前(英文 prefix):
```
feat(私有大厨): 加批量编辑(batch_edit.html + 渲染器)
fix(私有大厨): cooking_render 错误路径 exit 1
docs(私有大厨): P0-4 FAT 真测完成
test(私有大厨): FAT 模拟执行
```

✅ 之后(中文风格,match SKILLS):
```
[私有大厨] 加批量编辑(batch_edit.html + 渲染器)
[私有大厨] cooking_render 错误路径 exit 1
[私有大厨] P0-4 FAT 真测完成
[私大有厨] FAT 模拟执行
```

### 历史 commit 处理

历史 33 个 commit 保留不动(已 push,改 hash 风险大)。
新 commit 从本规则制定后开始用新格式。

## 参考来源

- SKILLS 仓库实测 5 个 SKILL commit 风格
- 对比项: prefix / type / 描述语言 / 标号
- 结论: SKILLS 仓库 100% 用 `[skill名] 描述` 中文风格

## 立即应用

下一个 commit 是 `B 任务:修 6 个 manager 错误路径 exit 1` 的 plan commit,使用新格式:

```
[私有大厨] 制定修 6 个 manager 错误路径 exit 1 的统一方案
```

而非:

❌ `docs(私有大厨): 制定修 6 个 manager 错误路径 exit 1 统一方案`
