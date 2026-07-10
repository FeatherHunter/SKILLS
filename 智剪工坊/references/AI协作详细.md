# AI 协作协议（详细）

> 本文档是 SKILL.md §🤖 AI 协作协议 的详细展开。
> SKILL.md 只列核心 4 原则 + 5 契约 + 3 反模式，详细条款见本文件。

## 1. 路由第一原则

**AI 拿到 intent.json / 用户需求后, 第一件事是查路由表**（`references/AI路由表-意图JSON字段枚举.md`）。

- 命中 → 调对应 用户脚本 CLI
- 不命中 → F 象限（明确说"智剪工坊当前不支持 X"）

**禁止**: AI 不查表直接调 CLI / 凭印象调参 / 静默不支持的功能

## 2. AI 文本解析 → 路由表匹配 → 用户确认（E 象限，v1.3 改）

**自由文本字段**（`notes` / `overall_intent` / `ending.prompt` 等）必须先匹配路由表：

1. 读字段
2. 在路由表里找匹配
   - 匹配成功 → 用对应 CLI
   - 匹配失败 → **不假装支持**, 告诉用户"智剪工坊当前不支持 X"
3. **先告知用户匹配结果, 等用户确认再调 CLI**

**反例**: 用户说"加个转场", AI 直接默认 `fade` → 错
**正例**: 用户说"加个转场", AI 列出 9 种 type 让用户选 → 对

## 3. 模糊项 / 待澄清（D 象限, AI 必问）

AI 看到模糊需求时**必须问用户**, 不擅自决定。常见模糊:

- "想要动感" → 问: 配 BGM？转场？调色？速度？
- "视频太长了" → 问: 剪头剪尾？cut-middle？target-duration？
- "加滤镜" → 问: color preset 选哪个？
- "开头加段音乐" → 问: 什么音乐？音量多少？全段还是开头？

### 3.1 ending.type 不在路由表时(v1.10 新增)

当 ending.type 是 `next-episode-promo` / `next-week` / 其他自定义类型时:

1. **AI 必须 fallback 到 `next-day` 实现**(黑屏 + 文字)
2. **AI 必须在回复里明确告知用户**:"ending.type X 不在标准路由表, 已 fallback 到 next-day"
3. **AI 禁止手写 ffmpeg drawtext 命令**(踩转义陷阱,用 `scripts/video/opening.py add` 替代)

ending.prompt 含特殊字符时:

- `\n` → AI 必须分行渲染(用 ffmpeg textfile + 多 drawtext,或多段 drawtext)
- emoji / 繁体 / 特殊符号 → AI 必须用 `escape_drawtext()`(opening.py 已实现)

### 3.2 AI 主动决策 vs 必须问的边界(v1.10 新增)

#### ✅ AI 可主动决策(无需问用户)

| 场景 | 示例 |
|---|---|
| 参数默认值 | BGM vol=0.15, crf=23, fps=30 |
| 重试失败任务 | 同方法重试 2 次 |
| 中间文件清理 | 临时变量命名 |
| 优化建议 | trim 精度 +1, 加 faststart |

#### ❌ AI 必须问用户(任何一条触发就问)

| 场景 | 反例(已踩过的坑) |
|---|---|
| 速度修改(speed-up/slow-down) | video_4 13.6 分钟冥想, AI 自作主张 4x(用户要 40x) |
| 风格调整(调色/滤镜/转场) | — |
| 新增/删除内容 | 字幕/封面/ending 缺失时自作主张 |
| intent.json 缺失关键字段 | 字幕诉求被漏掉 |
| ending.type 不在路由表 | 手写 ffmpeg 命令(应该 fallback + 提示) |
| 时长调整超过 ±10% | — |

#### 处理流程

1. 检测到以上任何场景 → 进入 D 象限(模糊项汇总),逐条问用户
2. 用户未明确时 → 用操作清单 D 象限列出,逐条问
3. **禁止**: AI 凭"行业惯例"或"看起来合理"自作主张

## 4. 速度范围 (speed-up / slow-down factor)

- `factor > 1.0` → 加速（如 2.0 = 2 倍速）
- `factor < 1.0` → 减速（如 0.5 = 半速）
- 推荐范围: 0.25 ~ 4.0（ffmpeg atempo 链能堆叠）
- **执行器二次校验（v1.0 强制）**：
  - `0.2 <= factor <= 10` → 正常
  - `10 < factor <= 100` → 高倍速（如冥想缩时），允许
  - `factor > 1000` → 报错退出，提示"几乎看不清，请确认"
  - `factor < 0.1` → 报错，提示"慢到几乎静止"
- 创作者填 `factor=90`（冥想 10 分钟缩到 7 秒）是合理用例

## 5. 时间字段解析规则 (pin-range / cut-middle / insert-image)

**v1.0 强制契约**：用户时间字段可能是**多种格式**。AI 必须**全兼容**，按以下顺序尝试：

| 写法 | 解析 | 示例 |
|---|---|---|
| `M:SS` 或 `MM:SS` | 标准格式 | `"1:30"` → 90s |
| `H:MM:SS` | 含小时 | `"1:30:00"` → 5400s |
| 纯数字（无单位） | **默认秒** | `"15"` → 15s |
| `"15秒"` / `"15s"` | 秒（中文/英文单位） | `"15秒"` → 15s |
| `"15分钟"` / `"15min"` | 分钟转秒 | `"15分钟"` → 900s |
| `"1分30秒"` | 复合 | `"1分30秒"` → 90s |
| 完全无法解析 | **必须问用户** | 不要瞎猜 |

- `parse_time()` 自动识别（详见 `lib/video_processing.py`，v1.7 改名）

## 6. 序列（sequences）是**部分约束**, 不是全连接

- `sequences[i].videos` 强制该 sequence 内部的视频顺序
- 但**不强制** sequence 间的视频不重复
- AI 必须读 `project.overall_intent` 决定 sequence 间的拼接方式

## 7. 自动读 intent.json 多版本 diff（v1.0 强制）

AI 收到 intent.json 后, **自动检查工作区里的版本文件**：

- `intent.json` (最新)
- `intent_v1.json` / `intent_v2.json` / ... (历史)

如果有多个版本:
- 自动 diff 所有字段变更
- 找出**哪些视频/字段被改**
- 重点关注变化区域, 不是重新理解全部

**创作者不需要**在 `history[].note` 手动写"我改了啥"——AI 自己读 diff 就懂。

## 8. 修改 用户脚本 CLI 后必须同步（v1.3 强制）

新增/修改 用户脚本 CLI 时, AI 必须:
1. 改 `scripts/{audio,asr,video,ai,batch}/<name>.py`
2. 同步改 `references/XX-xxx.md`(对应业务命名)
3. 同步改 SKILL.md 触发词索引（见 §能力链路完整性）
4. 在 `.archive/CHANGELOG.md` 加变更记录
5. (v1.7 _check_consistency.py 尚未实现，AI 自检清单已覆盖功能)

## 9. 真实照片 vs 插画

**封面图 / 内容图**都用 `cover_ai.py` 或 `matrix_generate_image` **生成插画**, **不放真实照片**。
- prompt 要写明 "扁平设计 / 插画 / illustration / 平面设计" 等关键词
- 创作者提供的 JPG 文件**可以**作为内容参考, 但封面不直接用

## 10. 新增 ops（v0.6+）

加新 op 必须:
1. 在 `lib/video_processing.py` 加 build filter（v1.7 改名，原 `lib/processing.py`）
2. 加到 §G.1 video 级 ops 表
3. 在 §H 路由表加字段定义
4. 在 `references/精剪-剪头剪尾保留段切中间.md` 或新建 references/ 加详细文档

**未实现的 op 触发 fallback**（v1.0 强制）：如果 intent.json 里有 ops 名称不在已知列表中, AI 应:
1. 读 op 的 note 字段看用户意图
2. 尝试用最接近的智剪工坊脚本实现
3. 在最终回复里告知"该 op 暂用 X 脚本模拟"