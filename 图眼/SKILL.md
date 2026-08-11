---
name: 图眼
description: >
  给无视觉模型(deepseek-v4-flash 等纯文本模型)装「眼睛」的视觉理解技能。
  用 mmx vision (MiniMax VLM) 把图片转成高保真文本描述。核心是「细节保真
  管线」:单次看图有损,精扫=切片+放大+逐片审计+审问循环,信息量约 10 倍。
  支持:看图(单次描述)、精扫(细节文档)、读图(OCR 提取文字)、问图(看图+
  提问→兜底大脑)、审图(审问循环)。图眼是纯眼睛:输出文本,调用者
  (deepseek 等 agent)自己就是大脑,通过 /图眼 调用本技能拿文本自行推理。
  输入支持本地文件 / URL / file-id。依赖:mmx-cli(已装)+ Pillow。
triggers:
  - 看图
  - 精扫
  - 读图
  - 问图
  - 审图
  - 图眼帮助
  - 帮我看看这张图
  - 仔细看这张图
  - 提取图里的文字
  - 这张图里有什么
  - 图里写了什么
  - 帮我读图
  - 细看
  - 审问这张图
metadata:
  requires:
    bins: [mmx]
    python: [Pillow]
  emoji: 👁️
---

# 图眼 👁️

**管什么**:给无视觉模型当眼睛——图片 → 高保真文本。
**不管什么**:不生成图片、不裁剪/美化图片(那是别的 skill);不内置推理大脑——
图眼只负责「看懂图片并把细节完整说出来」,推理由调用者(deepseek 等 agent)完成。

## 使用方式(核心)

**deepseek-v4-flash 等 agent 作为调用者时**:在对话里用 `/图眼` 调用本技能,
图眼返回图片的细节文本,调用者(自己就是大脑)基于文本继续推理。
**不存在 API key 的说法**:调用者就是大脑,图眼不会也不需要在内部再去调用
任何推理模型 API;只有 ask/audit 子命令内置的「兜底大脑」MiniMax-M3
(仅用于无大脑的纯 CLI 环境)会走 mmx text chat,而 mmx 凭据已配置好。

## 快速调用

```powershell
cd D:\2Study\StudyNotes\SKILLS\图眼

# ① 粗看:单次整体描述(1 次 vision,适合快速问答)
python scripts/eye.py look --image <图片路径或URL>

# ② 精扫:细节保真管线(10 次 vision,截图/文档/手写/审计用这个)
python scripts/eye.py scan --image <图片> --out <细节文档.md>

# ③ 读图:提取所有文字(OCR 专项)
python scripts/eye.py ocr --image <图片>

# ④ 问图:看图 + 提问 → 兜底大脑推理(仅无大脑环境;LLM agent 调用者直接用 ①②③)
python scripts/eye.py ask --image <图片> --question "问题"

# ⑤ 审图:兜底大脑审问循环(同上,仅供无大脑环境)
python scripts/eye.py audit --image <图片> --rounds 2 --out <收敛文档.md>
```

## 子命令速查

| 子命令 | 动作 | 次数 | 关键参数 |
|---|---|---|---|
| `look` | 粗看(单次整体描述) | 1 | `--image` `--prompt` `--out` |
| `scan` | 精扫(切片+审计+合并文档) | 10 | `--grid`(默认3) `--target`(1024) `--overlap`(0.12) `--out` |
| `ocr` | 读图(OCR 文字提取) | 1 | `--image` `--out` |
| `ask` | 问图(看图+问题→兜底大脑) | 10+1 | `--question` `--mode look/scan` `--out` |
| `audit` | 审图(兜底大脑审问循环) | 12-15 | `--rounds`(默认2) `--out` |

通用参数:`--output json`(全局,放子命令前)输出 `{status, data, message}` 契约;`--timeout` 默认 600s。

## 路由规则 · 用户表达 → 唤醒词 → CLI

| 用户表达示例 | 唤醒词 | CLI | 输出形式 |
|---|---|---|---|
| 帮我看看这张图是什么 / 这是什么图片 | 看图 | `look` | 描述文本 |
| 仔细看 / 精扫 / 截图里有什么细节 | 精扫 | `scan` | 细节文档(分区域) |
| 提取图里文字 / 图里写了什么 | 读图 | `ocr` | 纯文字 |
| 这张图里……?(带具体问题) | 问图 | `ask` | 问题+答案 |
| 帮我仔细核对/审计/审问这张图 | 审图 | `audit` | 收敛文档 |
| 图眼有什么能力 / 怎么用 | 图眼帮助 | `python scripts/eye.py --help` | HELP HTML |

### 输入形式

- **本地文件**:绝对路径,中文路径直接传(内部列表传参,无编码问题)
- **URL**:http(s) 自动下载到临时目录
- **file-id**:`file-xxx` 透传给 mmx(跳过 base64)

### 大脑关系(架构修正 v1.1)

- **图眼是纯眼睛**:只负责把图片变成高保真文本,输出给调用者。
- **调用者即大脑**:deepseek-v4-flash 等 agent 通过 `/图眼` 调用本技能,拿到文本后
  自己推理——不存在「图眼内部再调推理模型 API」的需求,也没有 API key 的说法。
- **兜底大脑 MiniMax-M3**:仅 `ask` / `audit` 子命令内置,供**无大脑的纯 CLI 环境**
  使用(走 mmx text chat,mmx 凭据已配置)。LLM agent 调用者应直接用 `look`/`scan`/`ocr`,
  不需要也不建议走 ask/audit。

### 歧义消解原则

1. 用户只说「看看这张图」没给问题 → 粗看 `look`
2. 用户给了具体问题(问内容/问文字) → `ask`(默认精扫模式)
3. 用户说「仔细/核对/审计」→ 精扫或审图,别用粗看糊弄
4. 用户给了图但没说干嘛 → 粗看 + 主动问要不要精扫
5. 图片路径不存在 → 报错带字段名,让用户修正

## 细节保真管线(为什么精扫有 10 倍信息量)

```
L1 全景   → 整体结构、空间关系              (1 次)
L2 切片   → 3×3 带 12% 重叠 + 放大 1024px    (9 次,细节主力)
L3 专项   → OCR / 数值提取(按需)            (1-3 次)
L4 审问   → 大脑生成追问 → 眼睛定向回答      (audit 模式)
```

单次看图是「有损压缩」——VLM 只挑它觉得重要的说,小字/角落/细节会被牺牲或幻觉。
切片精扫让每一块区域被独立放大审计,配合「宁多勿漏」审计 prompt,实测信息量提升约 10 倍
(1.5K → 15.4K 字符),并纠正粗看的文字幻觉。

## 输出位置约定

- 精扫/审图/问答文档默认 stdout 打印;`--out <path>` 落盘 markdown
- **SKILL 场景输出**:AI 应把落盘的 .md 用 `<media type="file">` 主动发送给用户(飞书 HTML 交付 v2 精神),不丢路径
- 临时切片/下载文件走 `tempfile` 系统临时目录,用完即弃,不污染仓库
- 本 skill 无数据库、无持久状态

## 硬规则(系统强制,无跳过通道)

| 规则 | 违反后果 |
|---|---|
| 图片必须存在(本地/URL/file-id 三选一) | 非零退出,报错含字段名 |
| 长文本兜底大脑调用走 `--messages-file`(防 Windows 命令行超长) | 内部强制,无绕过 |
| 所有错误 stderr + 非零退出码 | 静默失败=违规 |
| `--output json` 输出 `{status, data, message}` | 契约破坏=违规 |

## 软规则(AI 自觉,详见 references/prompts.md)

1. 逼细节不逼概括:审计用「报清单」prompt
2. 位置 > 散文:物体带方位,支撑审问
3. 宁可误报不可漏报
4. 大脑要诚实:信息不足就说缺什么,禁止编造
5. 切片重叠是刚需(默认 12%,密集小字 20%)
6. 文字类任务先 OCR 后审计

## 与其他 Skill 的边界

- 图片**生成**(文生图) → 走 mmx-cli 技能 / 智剪工坊
- 图片**处理**(裁剪/美化/调色) → 智剪工坊
- 视频**理解** → 智剪工坊 / video-motion-analyzer
- 本 skill 只负责:图片 → 文本(细节保真),以及可选文本模型推理

## 依赖与环境

- mmx-cli ≥ 1.0.15(已全局安装,API Key 已配置)——眼睛凭据
- Pillow(切片用;若缺执行 `pip install Pillow`)
- 调用者(大脑)= 使用本技能的 agent(如 deepseek-v4-flash),无需任何额外 API 配置

## 已验证可用

- ✅ `scan` 精扫:1024×1024 细节密集桌面图,9 片审计,15.3K 字符细节文档
- ✅ `ask` 问图(兜底大脑):精扫 + MiniMax-M3,按位置归类便签内容,诚实标注模糊项
- ✅ `ocr` 文字提取:手写便签 "Buy milk and eggs" 精确识别
- ✅ 15 项 pytest 全绿(切片逻辑 + CLI 契约,不碰网络)
- ✅ deepseek 调用场景:架构上由调用者消费文本即可,无需额外验证

## 已知问题 & 坑

1. **Windows 命令行长度限制**:>4KB 文本塞 `--message` 会报 "command line too long"——已强制走 `--messages-file`,勿改回。
2. **PowerShell 误报退出码**:脚本 stderr 有进度日志时,PowerShell 7 可能显示 `Command exited with code 1`,实际成功——以 stdout JSON 的 `status` 为准。
3. **手写体/模糊小字**:VLM 可能读错,大脑会标注置信度;关键场景用 `audit` 追问具体区域。
4. **超大图(>4K)**:先等比缩到 2048 再精扫,否则切片爆炸。
5. **审问轮数**:≤3 轮,每轮 ≤5 条追问,防成本失控。

## Changelog

- 2026-08-11 v1.1:架构修正——图眼定位为纯眼睛,调用者(deepseek 等 agent)即大脑;
  删除 `--brain deepseek`(不存在 deepseek API 集成);ask/audit 降级为「兜底大脑 MiniMax-M3,
  仅供无大脑 CLI 环境」;清理 research 临时产物,实证报告入 docs/。
- 2026-08-11 v1.0:初版。look/scan/ocr/ask/audit 五个子命令 + 细节保真管线 + 15 项测试 + references/prompts.md + HELP HTML。
