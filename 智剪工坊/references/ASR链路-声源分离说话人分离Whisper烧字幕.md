# ASR 链路 — 声源分离 + 说话人分离 + Whisper + 烧字幕

> **对应脚本**(7 个用户可见 CLI):
> - `scripts/audio/extract.py` — 提取音频
> - `scripts/audio/denoise.py` — 降噪
> - `scripts/audio/separate.py` — Demucs 声源分离(取人声)
> - `scripts/audio/diarize.py` — pyannote 说话人分离
> - `scripts/asr/transcribe.py` — Whisper 转录 → SRT
> - `scripts/asr/speaker_srt.py` — 说话人 + ASR 合并 → 带说话人 SRT
> - `scripts/asr/burn_subtitle.py` — SRT 烧录到视频
>
> **底层依赖**:`lib/asr/whisper.py`(faster-whisper)+ `lib/asr/pyannote.py`(pyannote.audio)
>
> **触发词**:ASR / Whisper / 语音转文字 / 说话人分离 / 声源分离 / 字幕 / 烧字幕 / 自动字幕 / 带说话人的字幕
>
> **何时加载**:**Step 9.2 粗加工(含 ASR) 或 Step 13 出片(含烧字幕) 时 AI 必读**
>
> **实测状态**:✅ 已验证 8 个 CLI 全部可跑(`--help` 通过)

---

## 1. 三档用户场景与对应链路

> **作为使用者,什么条件下会用到这套?** 详见下面 3 个场景。

### 场景 A — 单人说话(默认,90% 情况)

```
video.mp4 ─→ extract → audio.wav ─→ Whisper ─→ v.srt ─→ burn ─→ final.mp4
```

触发条件:**任意含人声的 vlog / 教学视频 / 日常记录**。

### 场景 B — 多人对话(2 人以上)

```
video.mp4 ─→ extract → audio.wav ─→ denoise ─→ separate(取人声) ─→ vocals.wav
                                       │
                                       ├→ diarize → diar.json
                                       └→ transcribe → v.srt
                                                        │
                                            speaker_srt 合并 ─→ v_speaker.srt
                                                        │
                                                     burn ─→ final.mp4
```

触发条件:**访谈 / 对谈 / 多人会议 / 辩论 / 圆桌**。

### 场景 C — 视频已有外部字幕(剪映/PR 烧过)

用户直接给 .srt 路径 → **跳过 Step 9.2**,只跑 Step 13 `burn_subtitle.py`。

触发条件:**用户已用剪映/PR 烧过字幕,导出 SRT 后给我**。

---

## 2. AI 在 Step 9.2 必须照下面的命令跑(中文版)

```bash
# 工作目录
cd <智剪工坊根目录>    # 智剪工坊根目录 = references/ 的上一级

# === 场景 A:单人(必跑 3 步)===
# Step 1: 提取音频(任何视频都要先做这步)
python scripts/audio/extract.py -i input.mp4 -o audio.wav

# Step 2 (可选,录音嘈杂才跑):降噪 6 种模式可选
python scripts/audio/denoise.py -i audio.wav -o clean.wav --mode afftdn
# 模式选择:afftdn / rnnoise / light / aggressive / wavelet / aap

# Step 3 (必跑):Whisper 转录
python scripts/asr/transcribe.py -i audio.wav --srt v.srt --model medium
# 中文必加 --lang zh 避免自动检测出错
python scripts/asr/transcribe.py -i audio.wav --srt v.srt --model medium --lang zh
# GPU 默认;CPU 切 --device cpu
python scripts/asr/transcribe.py -i audio.wav --srt v.srt --model medium --device cpu

# === 场景 B:多人(在 A 基础上加 3 步)===
# Step B1 (必跑):Demucs 声源分离取人声
python scripts/audio/separate.py -i clean.wav -o vocals.wav --stem vocals
# 默认用 htdemucs 模型(首次下载 ~300MB)

# Step B2 (必跑,需 HF token):说话人分离
python scripts/audio/diarize.py -i vocals.wav -o diar.json --token hf_xxxxxxxx
# 申请 token: hf.co/settings/tokens
# 接受 pyannote/speaker-diarization-3.1 模型协议

# Step B3 (必跑):合并说话人 + SRT
python scripts/asr/speaker_srt.py --diarize diar.json --srt v.srt --output v_speaker.srt

# === 场景 C:已自备字幕(只跑 Step 13)===
# 用户给 SRT 路径,直接跳过 9.2
```

---

## 3. AI 在 Step 13 出片必须照下面的命令跑

```bash
# 烧字幕(单人用 v.srt,多人用 v_speaker.srt)
python scripts/asr/burn_subtitle.py \
  --video input.mp4 \
  --srt v_speaker.srt \
  --output final.mp4 \
  --font-size 24
```

字幕样式默认(Microsoft YaHei / 字号 22 / 白字黑边 / 底部居中)。**样式定制**详见 `references/字幕文字-Whisper烧字幕片头变声.md`(不在本文档范围)。

---

## 4. AI 跑之前必读的硬规则

| # | 规则 | 违反后果 |
|---|------|----------|
| 1 | 必须先 `cd <智剪工坊根目录>` | `ModuleNotFoundError: common` |
| 2 | 中文场景必须加 `--lang zh` | 自动检测出错,识别成英文 |
| 3 | demucs 模型首次跑会下载 ~300MB,主动告知用户"在下载模型" | 用户以为卡住 |
| 4 | pyannote 需要 HuggingFace token + 接受模型协议 | 不接受协议会 401 |
| 5 | pyannote 模型首次下载 ~200MB,建议用户提前下完 | 同上 |
| 6 | Whisper `medium` 模型 ~1.5GB,GPU 默认;CPU 慢 10x | 长视频可能 OOM |
| 7 | demucs 分离出的人声用于 ASR 比直接 ASR 准确率提升 15-20% | 不分离 |
| 10 | **中国网络环境** HF 直连经常超时,设 `$env:HF_ENDPOINT = "https://hf-mirror.com"` 再跑 | 模型下载失败 |
| 8 | 输出 SRT 路径在工作区(如 `00_智剪/粗加工/sub.srt`),Step 13 才找得到 | 找不到 SRT |
| 9 | HF token 是用户隐私 — 建议用户存 .env,不要每次明文 --token | 暴露 token |

---

## 5. 失败排查清单(AI 拿到 stderr 后对照)

| 报错关键字 | 真问题 | 修复 |
|---|---|---|
| `ModuleNotFoundError: common` | 没 cd 到智剪工坊根目录 | Step 1 失败 |
| `faster_whisper 未安装` | 跳过了 `requirements.txt` 安装 | `pip install -r requirements.txt` |
| `pyannote/audio not found` | 同上 | `pip install pyannote.audio` |
| `No HuggingFace token` 或 401 | 跑说话人分离但没传 token / 没接受模型协议 | 让用户去 hf.co 申请 + 传 `--token` |
| `CUDA out of memory` | 模型太大或视频太长 | 改 `--device cpu` 或 `--model small` |
| `subtitles path` 报错 | SRT 路径有空格或中文 | 路径避免空格 |
| demucs / Whisper / pyannote 下载卡住 | huggingface 网络问题(中国常见) | **设镜像源** `$env:HF_ENDPOINT = "https://hf-mirror.com"` 后再跑 |

---

## 6. 完整链路 7 步速查表(复制即用)

```bash
# Step 1: 提取音频
python scripts/audio/extract.py -i input.mp4 -o audio.wav

# Step 2: 降噪(可选)
python scripts/audio/denoise.py -i audio.wav -o clean.wav --mode afftdn

# Step 3: 声源分离(仅多人)
python scripts/audio/separate.py -i clean.wav -o vocals.wav --stem vocals

# Step 4: 说话人分离(仅多人,需 HF token)
python scripts/audio/diarize.py -i vocals.wav -o diar.json --token hf_xxx

# Step 5: Whisper ASR
python scripts/asr/transcribe.py -i vocals.wav --srt v.srt --model medium --lang zh

# Step 6: 合并说话人 + SRT(仅多人)
python scripts/asr/speaker_srt.py --diarize diar.json --srt v.srt --output v_speaker.srt

# Step 7: 烧字幕(Step 13)
python scripts/asr/burn_subtitle.py --video input.mp4 --srt v_speaker.srt --output final.mp4 --font-size 24
```

---

## 7. 跟其他 references 的关系

- **references/主流程-阶段编排.md** Step 9.2:本文件必读
- **references/主流程-阶段编排.md** Step 13:本文件必读(出片清单)
- **references/字幕文字-Whisper烧字幕片头变声.md**:烧字幕的 drawtext 部分(打字机 / 9 宫格 / 跑马灯等高级效果)在该文档
- **references/音频链路-lib详解.md** §6:链路概览图
- **references/AI路由表-意图JSON字段枚举.md**:音视频 ops 字段枚举

---

## 8. 版本说明

- **v1.4 新增**:链路补全,新增降噪 / 声源分离 / 说话人分离
- **v1.5**:scripts/audio/*.py 调 lib/ffmpeg/audio/*.py(分层架构)
- **v1.7+**:本文档补回(原 ASR链路-...md 文件被误删)
- **v1.18+**:补 hf-mirror 镜像源(中国网络环境实测经验)