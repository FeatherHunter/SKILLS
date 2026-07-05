# 子技能 15 · digital-human(数字人 L2)

## 它是什么

用一张真人头像 + 文字/音频,生成"头像在说话"的视频。底层用 **mmx matrix_gen_videos subject 模式**(保持人脸一致)+ ffmpeg 合音频。

**Level:** L2(走 mmx 免费版)
- ✅ 头像图片 + 文案/音频 → 说话视频
- ✅ 327 个 TTS 声音(用文案模式时)
- ❌ 声音克隆(用自己的声音)— matrix MCP 不支持
- ❌ 嘴型精准对齐(L3 才有,SadTalkers 之类)

## 怎么用

### 用 mmx(默认,免费)

```bash
# 头像 + 文案(自动 TTS 合成音频 + 数字人视频)
python scripts/digital_human.py --avatar avatar.jpg --script "大家好我是帅猎羽" --output out.mp4

# 头像 + 现成音频
python scripts/digital_human.py --avatar avatar.jpg --audio voice.mp3 --output out.mp4

# 换声音(用 TTS 时)
python scripts/digital_human.py --avatar avatar.jpg --script "Hello" --voice male-qn-jingying --output out.mp4
```

### 用 HeyGen / D-ID(占位)

```bash
python scripts/digital_human.py --avatar avatar.jpg --audio voice.mp3 --api heygen --output out.mp4
# 需要 HEYGEN_API_KEY,完整实现待补
```

## 流程(2 步)

```
Step 1: matrix_gen_videos(avatar + subject 模式)
  ↓
  prompt: "A person speaking directly to camera, natural lip movements, ..."
  input_image: avatar.jpg
  reference_type: "subject"  ← 关键,保持人脸一致
  ↓
  输出:silent_video.mp4(6s,人脸动)

Step 2: ffmpeg 合音(silent + audio = final)
```

## 关键参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--avatar` | (必填) | 头像图片路径(人脸) |
| `--audio` | (二选一) | 音频文件 |
| `--script` | (二选一) | 文案(自动 TTS) |
| `--voice` | `male-qn-qingse` | TTS 声音(用 script 时) |
| `--out` | (必填) | 输出视频 |

## 头像要求

- ✅ 正脸(人脸检测得到)
- ✅ 单人(只处理第 1 张脸)
- ✅ JPEG / PNG
- ❌ 多人合照(可能只处理最大那张脸)

## 实测状态

- ✅ mmx 完整实现
- ⚠️ **未实测**(避免浪费 mmx API 配额)
- 预计:输入正脸头像 + 5s 文案 → 6s 数字人视频 + 音频

## 典型用例

1. **做课程讲解视频:** 真人头像 + 课件音频
2. **企业宣传片:** CEO 头像 + 旁白
3. **教学 vlog:** 不想露脸,用 AI 数字人代替
4. **多语言版 vlog:** 同一头像,不同语言配音

## 局限

- 嘴型不会精准对齐(只是"在动")
- 6s 限制(可多次拼接延长)
- 一致性可能有问题(每段人脸会略有差异)

## 进阶(未来)

- 用 SadTalkers(本地开源)做精准嘴型
- 多段拼接成长视频
- 加上字幕(auto_subtitle)

## 相关脚本

- 依赖:`scripts/rewrite_audio.py`(复用 TTS 函数)
- 同类:`scripts/text_to_video.py`(text-to-video)
- 前置:无
- 后置:无
