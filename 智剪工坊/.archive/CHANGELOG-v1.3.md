# v1.3 架构变更（2026-07-06）

## 核心变更：删除 step 脚本，AI 成为编排者

### 第一性原理

**之前（v1.2）**：
```
intent.json → AI 调 step 脚本 → step 脚本调 atomic CLI → ffmpeg
```
**问题**：step 脚本封装了 AI 该做的编排逻辑——AI 被绑定、流程被硬编码、失去灵活性。

**之后（v1.3）**：
```
intent.json → SKILL.md 文字描述 → AI 自己编排 → atomic CLI → ffmpeg
```
**原则**：AI 是编排者，原子 CLI 是工具，流程定义在 SKILL.md 文字（或 yaml）。

### 改动清单

**删除**（6 个 .py，已 trash）：
- `scripts/pipeline_step1_check.py`（解析 + 自检）
- `scripts/pipeline_step2_asr.py`（ASR 转录）
- `scripts/pipeline_step2_process.py`（单视频处理）
- `scripts/pipeline_step3_assemble.py`（sequence 拼接）
- `scripts/pipeline_step4_review.py`（模糊项兜底）
- `scripts/pipeline_step5_decide.py`（决策报告）

**改 SKILL.md**：
- §主能力总览：更新版本说明（v1.2 → v1.3）
- §阶段 2：删 step 脚本表 + 加"AI 编排原则" + 加"原子 CLI 路由参考表"
- §阶段 3：删错位的 step 脚本表 + 标注"待设计 + yaml 失效"
- §阶段 4：从 4 行文字升级为"AI 编排步骤表"（4 步 + 对应 CLI）

**改 scripts/README.md**：
- 删 "流程编排（pipeline_*）" 章节
- 命名约定：dimension 从 6 个 → 5 个（删除 pipeline）
- 添加新脚本 checklist：去掉 "加 §主体流程（如是 step 脚本）"
- 调用约定：去掉 "流程（pipeline）" 例

### 影响

**原子 CLI 层**：无影响（之前测过的转场 / 淡入淡出仍工作）

**AI 行为**：从"调 step 脚本"变成"自己编排原子 CLI"

**scripts 数量**：36 → 30（删 6 个 step）

### 验证

- xfade 9 种 type 全部通过（pre v1.3 测试）
- 转场 demo 13 个生成（pre v1.3 测试）
- post v1.3 验证：xfade + video_fade 调用成功，step 脚本调用 FileNotFoundError

### 遗留

- **阶段 3 模板工作流待设计**（你说"没想好"，跳过）
- **健身vlog.yaml 引用失效**（引用了已删的 modify.py / executor.py），需重写
- **end-to-end pipeline 测试未做**（单 op 测过，完整流水线未跑过）