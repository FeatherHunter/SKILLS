# 文字成片 - mmx免key生成6秒片段

> **对应脚本**: `scripts/ai/text_to_video.py`
> **触发词**: "文字成片"、"AI 生成视频"、"文生视频"
> **实测状态**: ✅ 验证通过

---

## 1. 调用范式

### 场景 1

```bash
# 默认用 mmx(免费)
python scripts/ai/text_to_video.py --prompt "A man running on a treadmill in a gym, cinematic" --output out.mp4

# 指定时长(6 或 10,mmx 强制)
python scripts/ai/text_to_video.py --prompt "A cat sitting on a sofa" --duration 6 --output out.mp4

# 试 Kling API(需 KLING_API_KEY)
python scripts/ai/text_to_video.py --prompt "..." --api kling --output out.mp4
```

## 2. 参数

| 参数 | 短选项 | 默认值 | 说明 |
|---|---|---|---|
| `--input` | `-i` | (必填) | 输入视频/音频/图片 |
| `--output` | `-o` | (必填) | 输出路径 |

## 3. 常见错误 / 限制

- **mmx 配额:** 每天 ~3 次(避免用完)
- **prompt 必须英文**(mmx 国际版,中文支持差)
- **时长固定 6s/10s**(mmx 限制)

## 4. 相关参考

- **SKILL.md §14 子技能索引**：本子技能的路由表
- **scripts/README.md**：scripts/ 目录命名规范（`<维度>_<动作>.py`）
- `.archive/CHANGELOG.md`：本子技能历史变更

---

<details>
<summary>📋 原文存档（v0.5 旧版，仅供 git history 追溯）</summary>

# 子技能 14 · text-to-video(文字成片 L2)

## 它是什么

从文字描述(英文 prompt)生成 6s/10s 短视频片段。底层用 **mmx matrix_gen_videos**,免费,无 API key。

**支持 API:**
- `matrix`(默认,推荐,免费) — mmx `matrix_gen_videos`
- `kling` / `vidu` / `runway`(占位,需外部 API key)
- `svd`(占位,需本地 GPU)

## 怎么用

```bash
# 默认用 mmx(免费)
python scripts/ai_text_to_video.py --prompt "A man running on a treadmill in a gym, cinematic" --output out.mp4

# 指定时长(6 或 10,mmx 强制)
python scripts/ai_text_to_video.py --prompt "A cat sitting on a sofa" --duration 6 --output out.mp4

# 试 Kling API(需 KLING_API_KEY)
python scripts/ai_text_to_video.py --prompt "..." --api kling --output out.mp4
```

## mmx 参数

- **duration:** 6 秒(1080P)或 10 秒(768P)
- **resolution:** 1080P(必须 6s)或 768P(必须 10s)
- **prompt:** 英文,描述动作+场景+风格

## 典型 prompt 写法

```
# 好的 prompt
"A young woman jogging in a park at sunrise, golden hour lighting, cinematic slow motion"

# 不好的 prompt(太抽象)
"运动"  # 没指定动作/场景/风格
```

**prompt 三要素:**
1. **主体:** 什么人/物
2. **动作:** 做什么
3. **场景 + 风格:** 在哪 + 什么视觉风格

## 实测状态

- ✅ mmx `matrix_gen_videos` 实现完成
- ⚠️ **未实测**(避免浪费 mmx API 配额:每天 3 次)
- mmx 视频生成一般需要 1-3 分钟

## 已知限制

- **mmx 配额:** 每天 ~3 次(避免用完)
- **prompt 必须英文**(mmx 国际版,中文支持差)
- **时长固定 6s/10s**(mmx 限制)

## 典型用例

1. **做封面 / B-roll 素材:** 一段健身房/户外场景插入 vlog
2. **生成 logo 动画:** 简单 logo 旋转 / 淡入
3. **做片头片尾:** 6s 主题视频

## 进阶(未来)

- 文案 → 多个视频片段 → 自动拼接(目前是单片段)
- 加上 narration(用 rewrite_audio)
- 完整 pipeline:文案 → 视频 + 音频 + 字幕 → 完整短片

## 相关脚本

- 依赖:无
- 同类:`scripts/ai_digital_human.py`(image-to-video subject 模式)
- 前置:无
- 后置:无


</details>
