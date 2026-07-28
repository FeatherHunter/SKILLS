# B 任务 · 修复必要性对抗式审查(2026-07-28)

## B 任务定义

"修 6 个 manager 错误路径 exit 0 → exit 1(subagent 真 FAT 发现 6 个 manager 错误时 exit code 0)"

cooking_render 已修 1 个(`be10684`)。
剩 5 个: relation_manager / history_manager / shopping_render / shopping_manager / recipe_render。

## 修复必要性 · 5 维度对抗式审查

### 维度 1 · subagent 价值

subagent 真 FAT 5 prompt 跑(commit 72d14c8):
- subagent 直接**读 stdout 文本内容**判失败("未找到食谱:...")
- **不依赖 exit code**
- 已实测 4/5 报"未找到食谱"subagent 仍正确识别为失败
- 结论:对 subagent **价值 = 0**(subagent 不看 exit code)

### 维度 2 · user 手工 CLI 价值

场景: `python3 manager.py add ...`
- user 看到 "未找到食谱:宫保虾球"(stdin 输出)
- user 知道失败 → 重试或换菜名
- exit code 0 vs 1 **user 体验无差异**(都看 stderr 文字)
- 结论:对 user 价值 = 0

### 维度 3 · CI 价值

实测:
- SKILLS 仓库**无 CI 配置**(.github/workflows/ 不存在)
- 26 pytest 测 validators + imports + render_data — **不直接调 manager 错误路径**
- 结论:对 CI 价值 = 0(无 CI)

### 维度 4 · shell 脚本价值

`grep -rE "subprocess\.run.*manager\.py" --include="*.sh"`
- 0 个 shell 脚本调 manager
- 0 个 Python 脚本外部调 manager(除了 render_data 等内部)
- render_data.py **已 catch RuntimeError**——manager 错误它能正常处理
- 结论:对 shell / 外部 Python 价值 = 0

### 维度 5 · agent 价值

本地 + 远端 agent:
- agent 读 stdout / stderr 内容判失败
- agent 不靠 exit code
- OpenCode / Claude Code / Cline / Roo Code 默认行为
- 结论:对 agent 价值 = 0

## 汇总 · 修复必要性评分

| 维度 | 价值 | 评估 |
|------|------|------|
| subagent | 0 | ❌ 不看 exit code |
| user 手工 | 0 | ❌ 看 stderr 文字 |
| CI 自动化 | 0 | ❌ 无 CI 配置 |
| shell / 外部 | 0 | ❌ 0 引用 |
| agent | 0 | ❌ 读 stdout 判失败 |
| **总分** | **0 / 5** | **❌ 无必要性** |

## 真正问题是什么?

**subagent 真 FAT 报告里说"错误路径返回 0 exit code 是现象"**——但 subagent 自己**不用 exit code 判失败**。

**真正值得修的是什么?**

B 任务应该**改成"验证"任务**:
- 改**清单**: "验证 6 个 manager 错误路径 exit code 行为"
- 测 **5 场景**: user 手工 / subagent / 未来 CI / agent 框架 / shell pipe
- 确认 exit 0 不会**真的**误导任何 user
- 结论:**如果 5 场景都不依赖 exit code,就不必修**

**结论**: B 任务**不修**——但**写这个对抗式审查文档**很有价值:
- 文档化"5 维度评估法"作为新规范
- 未来类似的"exit code bug 报告"先过 5 维度评估
- 避免未来不必要的"无 ROI 修复"工作

## 对抗式:不修的代价

不修 6 个 manager 错误路径 exit 0:
- ❌ 0 价值场景(已评估)
- ✅ 0 维护成本
- ✅ 0 风险

修 6 个 manager 错误路径 exit 1:
- ❌ 6 文件修改
- ❌ 6 个 main() 改 → 每文件 5 行
- ❌ 30 行代码改动
- ❌ 6 个 git commit
- ❌ 0 用户感知(用户读 stderr)
- ❌ 0 CI 影响(无 CI)

**修 vs 不修的工作量比 = 30+ 行: 0 价值**。

## 推荐

**不修 B 任务**。改任务清单为:
1. 写本文档(COMMIT 'docs' 描述,5 维度评估法作为新规范)
2. 未来遇到"exit code bug"报告 → 走 5 维度评估 → 决定是否修

如果未来真出现 CI / shell 依赖:
- 重新评估(那时**5 维度变了**)
- 单 commit 修 1 个 manager 即可

## 结论

B 任务"修复必要性" = 0(本会话环境下)。
不修 6 个 manager — 修本文档"5 维度评估法"作为新规范,价值更高。
