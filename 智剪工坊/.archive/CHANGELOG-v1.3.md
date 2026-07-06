# v1.3 协议层变更（2026-07-06）

## 核心变更：删除 step 脚本，AI 成为编排者

### 前后对比

**之前（v1.2）**:
```
intent.json → AI 调 step 脚本 → step 脚本调 atomic CLI → ffmpeg
```

**问题**: step 脚本封装了 AI 该做的编排逻辑——AI 被绑定、流程被硬编码、失去灵活性。

**之后（v1.3）**:
```
intent.json → SKILL.md 文字描述 → AI 自己编排 → atomic CLI → ffmpeg
```

**原则**: AI 是编排者，原子 CLI 是工具，流程定义在 SKILL.md 文字（或 yaml）。

---

## v1.3 完整 11 个优化

| # | 优化 | 实现 | 状态 |
|---|---|---|---|
| 1 | 粗加工 cover/ 目录 | SKILL.md §阶段 2 加 cover/ 子目录约定 | ✅ |
| 2 | BGM 来源 | mmx generate + 剪映路径写入 §阶段 2 | ✅ |
| 3 | voice 5 种扩展 | `original-with-bgm` 等加到 §H 枚举 + 路由表 | ✅ |
| 4 | 素材混合显示 | intent.html 列表"视频"→"素材"，正则加图片后缀 + data-zoom 放大 | ✅ |
| 5 | cut-middle multi-range | `processing.py` ranges 参数 + 段自动合并 + 10 测试通过 | ✅ |
| 6 | pin-range multi-range | `_build_pin_range_multi_filter` + 10 测试通过 | ✅ |
| 7 | 成片按 title 命名 | `lib/filename.py` + sanitize_filename（20/20 测试）+ get_output_path（4/4 测试）| ✅ |
| 8 | BGM 时间段/全段/音量 | `audio_bgm.py --start/--end/--bgm-fade-*` + 9 场景测试通过 | ✅ |
| 9 | BGM 时长不匹配 4 mode | loop / truncate / silence-end / ask | ✅ |
| 10 | 图片→视频 | `image_to_video.py` 原子 CLI + 8 场景测试 + 集成 concat 通过 | ✅ |
| 11 | 参数统一 video_normalize | `process_video` 末尾自动调 video_normalize | ✅ |

---

## 详细变更清单

### A. 删 step 脚本（6 个，已 trash）

- `scripts/pipeline_step1_check.py`（解析 + 自检）
- `scripts/pipeline_step2_asr.py`（ASR 转录）
- `scripts/pipeline_step2_process.py`（单视频处理）
- `scripts/pipeline_step3_assemble.py`（sequence 拼接）
- `scripts/pipeline_step4_review.py`（模板项兜底）
- `scripts/pipeline_step5_decide.py`（决策报告）

### B. 改 SKILL.md（v1.3 完整协议层）

- 主能力总览：更新版本说明（v1.2 → v1.3）
- 阶段 2：删 step 脚本段 + 加"AI 编排原则" + 加"原子 CLI 路由参考表"
- 阶段 3：删"已删 step 脚本" + 标注"待设计 yaml 失效"
- 阶段 4：从 4 行文字升级为"AI 编排步骤表（4 步 + 对应 CLI）"

### C. 改 scripts/README.md

- 删除"流程编排（pipeline_*）"章节
- 命名约定：dimension 从 6 个 → 5 个（删除 pipeline）
- 添加新脚本 checklist：去掉"加 → 主体流程（如是 step 脚本）"
- 调用约定：去掉"流程（pipeline）"词

### D. 新增 / 改 atomic CLI

| 脚本 | 变更 | 测试 |
|---|---|---|
| `video_xfade.py` | 9 种 type + TRANSITION_MAP + none/cut 短路 | 9/9 ✅ |
| `video_fade.py` | 单视频淡入淡出 | 4/4 ✅ |
| `video_freeze.py` | ending.type=freeze 用 | — |
| `video_normalize.py` | 30fps 归一化 | 集成 ✅ |
| `image_to_video.py` | **v1.3 新增** 图片→视频 | 8/8 ✅ |
| `audio_bgm.py` | **v1.3 新增** 4 mode + 时间段 + 淡入淡出 | 9/9 ✅ |
| `processing.py` | cut-middle / pin-range multi-range + auto video_normalize + log_info import fix | 10/10 ✅ |
| `lib/filename.py` | **v1.3 新增** sanitize_filename + get_output_path | 24/24 ✅ |

### E. SKILL.md 协议层加内容

- §G.1 19 个 video 级 ops（含 13 种 color preset）
- §G.2 9 种 sequence transitions + 映射表
- §H 字段枚举表 20+ 字段（新增 `project.title` / `videos[i].voice` 加 `original-with-bgm` / `output.bgm_match_mode` / 6 个 output 参数）
- §Jargon "AI 推断" 改"AI 文本解析 → 路由表匹配 → 用户确认"
- §BGM 来源（剪映路径 + mmx 生成）
- §工作区约定：粗加工加 `cover/` 子目录
- §阶段 4：成片按 `project.title` 命名 + `lib/filename.py` 调用
- 17 处"AI 推断"措辞统一替换
- **§G.1.b 图片素材**（v1.3 新增）：image_to_video 完整规则
- **pin-range / cut-middle multi-range 详细规则段**（v1.3 新增）

### F. intent.html 改

- 列表标题"视频"→"素材"，分别统计视频/图片数
- 过滤正则加 `.jpg/.jpeg/.png/.webp/.bmp`
- 图片卡 `data-zoom` 放大预览（CSS + JS 全屏 overlay）
- 素材混合显示（视频+图片同一列表）
- 加 `project.title` 输入框

### G. 模板

- `模板/健身vlog.yaml` v1.3 重写（4 stage: rhythm/order/transitions/data_overlay）

---

## v1.3 渐进式披露重构（2026-07-06 第二轮）

**问题**: SKILL.md 1336 行，AI 看不完。

**方案**: SKILL.md 变索引（~400 行），详细内容按"何时需要"拆到 `references/`。

**新 references/ 文件**:

- `02-routing.md`（v1.3 新增，**阶段 1 必读**）：字段枚举表 + 完整路由表 + E 象限匹配规则
- `03-stages.md`（v1.3 新增，**阶段 2-4 必读**）：阶段 1-4 AI 编排详细步骤
- `04-cut.md`（v1.3 新增）：pin-range / cut-middle multi-range 详情
- `05-image.md`（v1.3 新增）：image_to_video + Ken Burns 详情
- `07-audio.md`（v1.3 改）：audio_bgm 4 mode + 时间段 + 淡入淡出

**SKILL.md 行数变化**: 1336 → 409（-927 行，-69%）。

---

## BUG 修复（v1.3.1, 2026-07-06）

| # | BUG | 修复 |
|---|---|---|
| 1 | `concatenate_simple(output_path: str)` 调 `.parent.mkdir()` 崩 | `output_path = Path(output_path) if not isinstance(output_path, Path) else output_path` |
| 2 | `process_video(output_path: str)` 同样问题 | 同上 |
| 3 | `image_to_video.py` 参数 `--zoom-in/out` 跟 `transitions[].type='zoom-in'` 命名冲突 | 改为 `--ken-burns-in/out` + intent 字段同步 |
| 4 | `processing.py` v1.3 集成 `video_normalize` 用了 `log_info` / `log_warn` 但没 import | 加 import + fallback |

---

## 测试覆盖（60+ 严格测试 0 BUG）

| 类别 | 数量 | 来源 |
|---|---|---|
| 转场 9 种 type | 9 | `_test_xfade` |
| 单视频淡入淡出 4 种 | 4 | `_test_fade` |
| ending 4 种风格 | 4 | `_test_ending` |
| BGM 9 场景（默认/中段/开头/结尾/短段/silence-end/fade/边界/边界）| 9 | `_test_bgm_all_scenarios` |
| cut-middle multi-range 6 场景 | 6 | `_test_multi_range` |
| pin-range multi-range 4 场景 | 4 | `_test_multi_range` |
| image_to_video 8 场景（含集成）| 8 | `_test_image_to_video` |
| BUG 修复验证 5 场景 | 5 | `_test_bugfix_v131` |
| filename 24 测试 | 24 | `_test_filename` |
| 视频 clip 预处理 | 5 | `_test_clip` |

**总计 76 个测试, 0 BUG**。

---

## 已知限制（v1.3 留待解决）

1. **AI 编排是原则不是机制**：SKILL.md 写满"AI 必读"但没 executor 强制。别的 AI 可能跳过路由表。
2. **end-to-end pipeline 集成测试未做**：单 op 测过 76 次，完整 4 阶段未跑（用户晚上手工测）。
3. **`photo` 字段在 intent.html 已加，但 11 个优化只做了"图片→视频"CLI，UI 测试未做**。
4. **`cover.type='image'` 当前不支持**（intent.html 没字段承载图片路径）——AI 必须告知用户"改用 ai 或 text"。
5. **ken-burns 视觉效果待真实素材验证**：测试用的纯色图，没真实照片测试。
6. **BGM 时间段测试用 5s 短 BGM + 30s 静音视频**：真实 BGM 长度 30-60s 的情况没测。
