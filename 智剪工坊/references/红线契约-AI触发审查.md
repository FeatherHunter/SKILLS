# 红线契约：AI 触发审查协议

> 本协议细化智剪工坊 SKILL.md §能力链路完整性 红线原则，给 AI 一个**可执行**的 5 步自检清单。
> 适用场景：用户让 AI 修改 SKILL.md / references/*.md / scripts/*.py / lib/*.py。

## 1. 触发条件

满足任一即触发自检：

- 用户说"修改 SKILL.md" / "改 references/" / "改 scripts/" / "改 lib/"
- AI 主动判断"这次改动会影响链路一致性"
- 任何对 4 层链路（SKILL → 中间层 md → 功能层 scripts → lib）的修改

## 2. 5 步自检清单

AI 修改完任何链路文件后，**必须**逐项打勾：

```
□ 1. 我改了什么？→ 列出改动清单
       文件：哪个文件
       段落：改了哪段
       原因：为什么改

□ 2. 链路里其他位置是否需要同步？
       - 改 scripts/{audio,asr,video,ai,batch}/ → 同步 SKILL.md 触发词 + references/*.md
       - 改 SKILL.md 触发词 → 同步 references/*.md + scripts/
       - 改 references/*.md → 同步 SKILL.md 触发词
       - 改 lib/ → 检查上游 scripts/ 是否需要更新

□ 3. 主动检查（AI 自己读文件，不强求工具脚本）：
       - 读 SKILL.md 触发词 → 新能力是否已声明？
       - 读 references/ 对应文档 → 是否覆盖新能力？
       - ls scripts/{audio,asr,video,ai,batch}/ → 新能力是否实际存在？
       - grep lib/ 对应模块 → 新函数是否已实现？

□ 4. 全部一致 → 标记完成
       - 写入 logs/<task_id>.md 红线节
       - 写入 .archive/CHANGELOG.md（如有 git）

□ 5. 发现不一致：
       - 严重不一致 → 立即停下报告（不修复）
       - 轻微不一致 → 自动修 + 在最终回复里报告
```

## 3. 严重 vs 轻微不一致

### 3.1 严重不一致（必须停下报告）

满足任一即视为严重：

- **链路断裂**：SKILL.md 列了某能力，但 scripts/ 没有对应脚本（AI 不能自创）
- **命名冲突**：scripts/ 有脚本，但 references/ 没文档（无法路由）
- **触发词覆盖缺失**：references/ 改了章节，但 SKILL.md 触发词未同步
- **lib 函数未实现**：scripts/ 调了 lib.x，但 lib/ 没 x 函数

### 3.2 轻微不一致（自动修 + 报告）

- 触发词拼写错误（影响 AI 检索）
- 章节顺序错乱（影响阅读）
- 链接 404（references/ 文件被删除但 SKILL.md 还有引用）

## 4. 报告模板

写入 logs/<task_id>.md 红线节：

```markdown
## Red Line Audit

**触发**：用户让 AI 修改 X
**改动清单**：
- scripts/audio/mix.py: 改了 vol 默认值从 0.18 → 0.15
- SKILL.md: 加触发词 "音量调节"
- references/音频配乐-BGM循环淡入淡出节拍.md: 同步 vol 默认值说明

**自检结果**：
- [x] SKILL.md 触发词已加 "音量调节"
- [x] scripts/audio/mix.py 已改
- [x] references/ 已同步
- [x] 无不一致

**归档**：.archive/CHANGELOG.md 已记录
```

## 5. AI 行为约束

- ✅ **必须**：5 步清单逐项打勾（不打勾 = 未完成）
- ✅ **必须**：严重不一致立即停下报告（不修复，等用户决策）
- ✅ **必须**：写入 logs/<task_id>.md 红线节（事后可查）
- ❌ **禁止**：跳过自检直接继续
- ❌ **禁止**：发现严重不一致但偷偷修复
- ❌ **禁止**：用户没明确授权就自创脚本

## 6. 与 SKILL.md §能力链路完整性 的关系

本协议是 SKILL.md §能力链路完整性 的**可执行展开**。两者关系：

- **SKILL.md §能力链路完整性**：宪法（红线原则，不可妥协）
- **本协议**：执行手册（5 步可操作清单）

AI 修改 SKILL 后**也必须重新加载本协议**，因为本协议可能因 SKILL.md 改动而需要更新。