# 子技能 13 · rewrite-audio(改词翻唱 L2)

## 它是什么

两段式 agent-driven 流程:**Whisper 转录 → agent 改写文案 → matrix TTS 合成 → ffmpeg 替换音轨**。把视频的音轨替换成 AI 生成的新版本。

**核心创新:** LLM 判断放在 Mavis agent(我)这边,**不走 daemon subprocess,避开 token 失效问题**。

## 工作流

```
你的 vlog 视频
  ↓
transcribe: Whisper → SRT + words.json
  ↓
(agent) 读 SRT,改写/翻译/换风格
  ↓
synthesize: 改写文案 → MP3 (matrix TTS, 327 个预置声音)
  ↓
replace: 视频 + MP3 → 新视频(ffmpeg)
  ↓
输出新视频(画面不变,音轨替换)
```

## 怎么用

### 完整 agent-driven 流程

```bash
# 1. 转录
python scripts/rewrite_audio.py transcribe --input v.mp4 --srt v.srt

# 2. (Mavis 读 SRT,改写文案,告诉你用哪个 voice_id)

# 3. 合成新音频
python scripts/rewrite_audio.py synthesize --text "改写后的文案" --voice male-qn-jingying --out v_new.mp3

# 4. 替换音轨
python scripts/rewrite_audio.py replace --video v.mp4 --audio v_new.mp3 --out v_final.mp4
```

### 子命令速查

```
transcribe  视频 → SRT + words.json
synthesize  文本 → MP3 (matrix TTS)
replace     视频 + 音频 → 新视频
```

## TTS 声音(327 个预置)

| 中文常用 | 描述 |
|---|---|
| `male-qn-qingse` | 青涩青年音色(默认) |
| `male-qn-jingying` | 精英青年音色 |
| `male-qn-badao` | 霸道青年音色 |
| `male-qn-daxuesheng` | 青年大学生音色 |
| `female-shaonv` | 少女音色 |
| `female-yujie` | 御姐音色 |
| `female-chengshu` | 成熟女性音色 |
| `female-tianmei` | 甜美女性音色 |
| `Chinese (Mandarin)_Gentleman` | 温润男声 |
| `Chinese (Mandarin)_Male_Announcer` | 播报男声 |
| `Chinese (Mandarin)_Lyrical_Voice` | 抒情男声 |

**完整列表:** `mavis mcp call matrix matrix_get_voice_list '{}'`

## 典型应用场景

1. **口播改简洁:** 啰嗦版 → 简洁版
2. **中翻英:** 出海 B 站海外版用(注:复杂翻译建议 LLM agent 直接做)
3. **换声:** 自己声音不好听,用磁性/温润/专业 声音
4. **改风格:** 原版太正经 → 改成轻松/幽默/正式

## 实测性能(端到端 demo)

- 输入:test_speech.mp4(20s TTS 测试)
- 改写:删水词 + 改写(`嗯其实...然后...` → `今天聊减肥...`)
- 换声:`male-qn-qingse` → `male-qn-jingying`
- 输出:test_speech_rewritten.mp4(11.8s,省 41% 时长)

## 局限

- L3 声音克隆(用自己的声音)**做不到**:matrix MCP 只暴露 327 个预置声音
- 短句换声比长句更自然(整段 60+ 字 TTS 偶尔会卡)
- 整段 TTS 速度由 1×(单句)到 5×(多句 batch)可选,本脚本用单句

## 进阶:用 batch 加速

matrix 也有 `matrix_batch_text_to_audio`,一次最多 10 句。后续可以加 `synthesize-batch` 子命令,本脚本暂未实现。

## 相关脚本

- 依赖:`scripts/remove_fillers.py`(复用 transcribe 逻辑)
- 同类:`scripts/digital_human.py`(也用 TTS)
- 前置:无
- 后置:无
