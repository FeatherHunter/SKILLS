---
name: glm-ocr-to-en-word
description: 基于智谱GLM-OCR API的PDF扫描件转英文Word文档技能。采用逐页并行处理模式，Python脚本负责OCR识别和Word构建，AI负责翻译。支持子代理并行翻译、断点续传、完整日志记录。提供两种方案：方案一（layout_details精确还原）和方案二（Markdown+pandoc）。
trigger:
  - "PDF转英文Word"
  - "PDF转英文docx"
  - "扫描件转英文Word"
  - "GLM-OCR转英文Word"
  - "PDF识别转英文Word"
  - "PDF中译英Word"
  - "扫描件翻译转Word"
---

# glm-ocr-to-en-word 基于GLM-OCR的PDF转英文Word文档技能

## 技能概述

本技能采用**逐页并行处理模式**，将PDF逐页处理，每页生成独立文件，支持子代理并行翻译，保留完整过程痕迹和日志。

**核心流程**：

```
PDF → [逐页OCR] → [子代理并行翻译] → [逐页构建Word] → [合并]
```

**核心优势**：

| 特性 | 说明 |
|------|------|
| 无上下文污染 | 每页独立处理，子代理只处理单页 |
| 过程可追溯 | 每页独立文件，完整日志记录 |
| 并行加速 | 支持子代理并行翻译，大幅提升速度 |
| 断点续传 | 页级粒度，任意步骤可中断恢复 |
| 日志排查 | 每个环节写入日志文件，便于问题定位 |

---

## 开场交互式询问

**AI必须在开始任何处理前，先询问用户选择方案：**

```
【方案选择】

检测到PDF转英文Word请求，请选择处理方案：

方案一：layout_details精确还原（推荐）
  - 使用GLM-OCR的结构化JSON数据
  - python-docx精确还原表格、图片位置
  - 支持复杂表格合并、元素定位
  - 适合：复杂排版、含表格/图片的文档

方案二：Markdown + HTML + pandoc（推荐）
  - 使用GLM-OCR的Markdown输出
  - MD转HTML（保留HTML表格含colspan/rowspan）
  - pandoc -f html 转换为Word，配合reference.docx模板控制字体样式
  - 适合：含复杂表格的文档，表格合并单元格支持好

请回复 "方案一" 或 "方案二"
```

---

## 日志机制

**所有脚本自动记录日志到 `temp/logs/` 目录**：

```
temp/logs/
├── step1_ocr.log              ← 阶段1 OCR日志
├── step2_translate.log        ← 阶段2 翻译日志（AI追加）
├── step3_build_word.log       ← 阶段3 Word构建日志
└── step4_merge.log            ← 阶段4 合并日志
```

### 日志格式

每条日志包含：时间戳、级别、页码（如有）、操作、详情

```
[2025-04-19 12:00:00] [INFO] [Page 1] OCR开始
[2025-04-19 12:00:05] [INFO] [Page 1] OCR完成，元素数: 15
[2025-04-19 12:00:05] [INFO] [Page 1] 图片下载: 2张
[2025-04-19 12:00:10] [ERROR] [Page 3] OCR失败: API超时
[2025-04-19 12:00:15] [INFO] [Page 3] 重试成功
```

### 日志用途

1. **问题排查**：某页翻译质量差，查看该页日志定位原因
2. **断点恢复**：读取日志确定哪些页已完成
3. **性能分析**：统计各阶段耗时

---

## 文件结构

### 方案一文件结构

```
temp/
├── logs/
│   ├── step1_ocr.log              ← OCR日志
│   ├── step2_translate.log        ← 翻译日志
│   ├── step3_build_word.log       ← Word构建日志
│   └── step4_merge.log            ← 合并日志
├── manifest.json                  ← 逐页处理清单
├── images/                        ← 下载的图片
├── page_1_ocr.json                ← 第1页OCR原始结果
├── page_2_ocr.json                ← 第2页OCR原始结果
├── ...
├── page_1_translated.json         ← 第1页翻译结果
├── page_2_translated.json         ← 第2页翻译结果
├── ...
├── layout_details_final.json      ← 翻译结果合并文件
├── word_pages/                    ← 逐页Word存放目录
│   ├── page_1_en.docx
│   ├── page_2_en.docx
│   └── ...
└── （最终输出文件在temp外）
```

### 方案二文件结构

```
temp/
├── logs/
│   ├── step1_ocr.log
│   ├── step2_translate.log
│   ├── step3_build_word.log
│   └── step4_merge.log
├── manifest.json
├── images/
├── page_1.md                      ← 第1页OCR Markdown
├── page_2.md
├── ...
├── page_1_translated.md           ← 第1页翻译后Markdown
├── page_2_translated.md
├── ...
├── word_pages/
│   ├── page_1_en.docx
│   └── ...
└── （最终输出文件在temp外）
```

---

## 方案一：layout_details精确还原

### 执行分工

| 阶段 | 执行者 | 职责 | 日志文件 |
|------|--------|------|----------|
| 阶段1：逐页OCR | Python脚本 | 调用API，保存JSON/MD，下载图片 | step1_ocr.log |
| 阶段2：并行翻译 | **AI/子代理** | 逐页翻译，保存结果，质量验证 | step2_translate.log |
| 阶段3：构建Word | Python脚本 | 逐页构建Word | step3_build_word.log |
| 阶段4：合并Word | Python脚本 | 合并所有页为最终文档 | step4_merge.log |

### 前置要求

#### 必须提供：智谱GLM-OCR的API Key

1. 注册智谱开放平台：https://open.bigmodel.cn
2. 在API Keys页面创建密钥
3. 执行前告知API Key

#### 依赖安装

```bash
pip install python-docx beautifulsoup4 requests pypandoc
```

---

### 阶段1：Python脚本 - 逐页OCR识别

#### 运行命令

```bash
python scripts/step1_ocr.py "PDF路径" "API_KEY"
```

#### 脚本行为

1. 逐页调用GLM-OCR API
2. 每页保存 `page_N_ocr.json` 和 `page_N.md`
3. 下载图片到 `images/`
4. 生成 `manifest.json` 清单
5. 所有操作写入 `logs/step1_ocr.log`

#### 日志示例

```
[2025-04-19 12:00:00] [INFO] ========== 阶段1：逐页OCR开始 ==========
[2025-04-19 12:00:00] [INFO] PDF路径: xxx.pdf
[2025-04-19 12:00:00] [INFO] PDF大小: 9.3MB
[2025-04-19 12:00:01] [INFO] [Page 1] 开始OCR
[2025-04-19 12:00:06] [INFO] [Page 1] OCR完成，元素数: 15，Token: 6124
[2025-04-19 12:00:06] [INFO] [Page 1] 图片下载: page_1_img_0.png
[2025-04-19 12:00:07] [INFO] [Page 1] 保存: page_1_ocr.json
[2025-04-19 12:00:07] [INFO] [Page 2] 开始OCR
...
[2025-04-19 12:05:00] [INFO] ========== 阶段1完成 ==========
[2025-04-19 12:05:00] [INFO] 总页数: 24
[2025-04-19 12:05:00] [INFO] 总Token: 146765
[2025-04-19 12:05:00] [INFO] 清单文件: temp/manifest.json
```

#### 断点续传

- `page_N_ocr.json` 已存在则跳过该页
- 日志记录跳过原因

---

### 阶段2：AI并行翻译（核心）

#### ⚠️ 强制规则

**阶段2必须由AI直接执行翻译，不得使用任何Python脚本替代。**

可用脚本 | 功能
--------|-----
scripts/step2_helper.py validate | 验证质量（检查残留中文）
scripts/step2_helper.py merge | 合并结果

---

#### 子代理并行翻译

**AI读取 `manifest.json` 获取总页数，分批调度子代理并行翻译**

##### 调度计划输出

```
【并行翻译调度计划】
- 总页数: 24
- 并行度: 4（每批处理4页）
- 分批计划:
  第1批: 页1-4
  第2批: 页5-8
  第3批: 页9-12
  第4批: 页13-16
  第5批: 页17-20
  第6批: 页21-24

开始调度子代理并行翻译...
```

##### 子代理任务模板

```
你是一个翻译子代理。请完成以下任务：

1. 用Read工具读取 temp/page_{N}_ocr.json
2. 翻译该页所有元素的content字段（中文→英文）
   - 不翻译：数字、批号、化学式、图片路径、HTML标签本身
   - 翻译：中文术语、中文句子、表格单元格文本
3. 用Write工具保存翻译结果到 temp/page_{N}_translated.json
4. 运行验证：python scripts/step2_helper.py validate "temp/page_{N}_translated.json"
5. 如有残留中文，补充翻译并重新验证
6. 完成后返回：页码、元素数量、验证结果（chinese_count）
```

##### AI记录翻译日志

每批子代理完成后，AI追加日志到 `logs/step2_translate.log`：

```
[2025-04-19 12:10:00] [INFO] ========== 阶段2：并行翻译开始 ==========
[2025-04-19 12:10:00] [INFO] 总页数: 24，并行度: 4
[2025-04-19 12:10:05] [INFO] [Batch 1] 启动子代理处理页1-4
[2025-04-19 12:10:30] [INFO] [Page 1] 翻译完成，元素数: 15，chinese_count: 0
[2025-04-19 12:10:31] [INFO] [Page 2] 翻译完成，元素数: 12，chinese_count: 0
[2025-04-19 12:10:32] [WARN] [Page 3] 翻译完成，chinese_count: 2，需补充翻译
[2025-04-19 12:10:35] [INFO] [Page 3] 补充翻译完成，chinese_count: 0
[2025-04-19 12:10:40] [INFO] [Batch 1] 完成
...
[2025-04-19 12:15:00] [INFO] ========== 阶段2完成 ==========
```

##### 翻译质量验证

每页翻译后必须验证：

```bash
python scripts/step2_helper.py validate "temp/page_N_translated.json"
```

验证结果写入日志，chinese_count > 0 则补充翻译后重新验证。

---

#### 翻译规则（严格遵守）

**禁止翻译的数据**：
- 数字（如：250mg, 20240101, 97.5%, 200万）
- 日期（如：2025年09月18日 → 转换为 2025-09-18）
- 批号、编号、编码
- 化学式、分子式
- 图片路径（保持原路径不变）
- HTML标签本身（只翻译标签内的文本）

**必须翻译的内容**：
- 中文术语 → 英文（根据上下文理解）
- 中文句子 → 英文句子
- 表格单元格文本 → 英文（保留HTML结构）

---

### 阶段3：Python脚本 - 逐页构建Word

#### 运行命令

```bash
# 对每页执行（可并行）
python scripts/step3_build_word.py "temp/page_N_translated.json" "temp/word_pages/page_N_en.docx"
```

#### 日志示例

```
[2025-04-19 12:20:00] [INFO] ========== 阶段3：逐页构建Word开始 ==========
[2025-04-19 12:20:01] [INFO] [Page 1] 读取: page_1_translated.json
[2025-04-19 12:20:02] [INFO] [Page 1] 元素数: 15，表格数: 2
[2025-04-19 12:20:03] [INFO] [Page 1] 保存: word_pages/page_1_en.docx
[2025-04-19 12:20:04] [INFO] [Page 2] 读取: page_2_translated.json
...
[2025-04-19 12:25:00] [INFO] ========== 阶段3完成 ==========
```

---

### 阶段4：Python脚本 - 合并Word

#### 运行命令

```bash
python scripts/step4_merge_word.py "输出_en.docx" --dir "temp/word_pages"
```

#### 日志示例

```
[2025-04-19 12:30:00] [INFO] ========== 阶段4：合并Word开始 ==========
[2025-04-19 12:30:00] [INFO] 输入目录: temp/word_pages
[2025-04-19 12:30:00] [INFO] 找到24个Word文件
[2025-04-19 12:30:01] [INFO] 合并: page_1_en.docx
[2025-04-19 12:30:02] [INFO] 合并: page_2_en.docx
...
[2025-04-19 12:30:30] [INFO] ========== 阶段4完成 ==========
[2025-04-19 12:30:30] [INFO] 输出文件: 输出_en.docx
[2025-04-19 12:30:30] [INFO] 文件大小: 120.5 KB
```

---

## 方案二：Markdown + HTML + pandoc（推荐）

### 核心流程

```
MD → HTML(保留HTML表格) → pandoc -f html → Word
```

### 关键技术

1. **MD转HTML**：保留原始HTML表格（含colspan/rowspan），非表格内容转为HTML标签
2. **pandoc -f html**：从HTML输入，完整支持表格合并单元格
3. **reference.docx模板**：控制输出Word的字体、字号、行距等样式

### 模板文件

`templates/reference.docx` 定义了输出Word的默认样式：
- Normal样式：Times New Roman 12pt，1.5倍行距
- 表格：Times New Roman 10pt

### 执行分工

| 阶段 | 执行者 | 职责 | 日志文件 |
|------|--------|------|----------|
| 阶段1：逐页OCR | Python脚本 | 调用API，保存Markdown | step1_ocr.log |
| 阶段2：并行翻译 | **AI/子代理** | 逐页翻译Markdown | step2_translate.log |
| 阶段3：转Word | Python脚本 | MD→HTML→pandoc→Word | step3_build_word.log |
| 阶段4：合并Word | Python脚本 | 合并所有页 | step4_merge.log |

### 完整流程

```
1. 阶段1（Python脚本 - 逐页OCR）
   python scripts/step1_ocr.py "PDF路径" "API_KEY"
   → 输出: temp/page_N.md, temp/manifest.json
   → 日志: temp/logs/step1_ocr.log

2. 阶段2（AI - 子代理并行翻译）
   → 读取 manifest.json，分批调度子代理
   → 每页读取 page_N.md，翻译保存 page_N_translated.md
   → 逐页验证: python scripts/step2_md_helper.py validate
   → 追加日志: temp/logs/step2_translate.log

3. 阶段3（Python脚本 - 逐页转Word）
   python scripts/step3_md_to_word.py "temp/page_N_translated.md" "temp/word_pages/page_N_en.docx"
   → 内部流程: MD → HTML → pandoc -f html --reference-doc → Word
   → 自动使用 templates/reference.docx 模板
   → 日志: temp/logs/step3_build_word.log

4. 阶段4（Python脚本 - 合并）
   python scripts/step4_merge_word.py "输出_en.docx" --dir "temp/word_pages"
   → 日志: temp/logs/step4_merge.log
```

### 子代理任务模板（方案二）

```
你是一个翻译子代理。请完成以下任务：

1. 用Read工具读取 temp/page_{N}.md
2. 翻译Markdown内容（中文→英文）
   - 保留Markdown格式标记（#, *, -, >, |, ``` 等）
   - 保留数字、批号、化学式
3. 用Write工具保存翻译结果到 temp/page_{N}_translated.md
4. 运行验证：python scripts/step2_md_helper.py validate "temp/page_{N}_translated.md"
5. 如有残留中文，补充翻译并重新验证
6. 完成后返回：页码、验证结果（chinese_count）
```

---

## 断点续传机制

### 检查点文件

| 阶段 | 检查点文件 | 存在则跳过 |
|------|-----------|-----------|
| 阶段1 | page_N_ocr.json / page_N.md | 跳过该页OCR |
| 阶段2 | page_N_translated.json / page_N_translated.md | 跳过该页翻译 |
| 阶段3 | word_pages/page_N_en.docx | 跳过该页Word构建 |
| 阶段4 | 最终输出文件 | 跳过合并 |

### 日志辅助断点

```bash
# 查看哪些页已完成OCR
grep "OCR完成" temp/logs/step1_ocr.log

# 查看哪些页翻译有问题
grep "chinese_count: [1-9]" temp/logs/step2_translate.log
```

---

## 常见问题排查

### 问题：某页翻译质量差

```bash
# 1. 查看该页日志
grep "\[Page N\]" temp/logs/step2_translate.log

# 2. 对比原始和翻译后文件
diff temp/page_N.md temp/page_N_translated.md

# 3. 重新翻译该页
# 删除 page_N_translated.md，重新调度子代理
```

### 问题：OCR失败

```bash
# 查看OCR日志
grep "ERROR\|WARN" temp/logs/step1_ocr.log

# 手动重试该页
python scripts/step1_ocr.py "PDF路径" "API_KEY" --page 5
```

### 问题：Word构建失败

```bash
# 查看构建日志
grep "ERROR" temp/logs/step3_build_word.log

# 检查翻译JSON格式
python -m json.tool temp/page_N_translated.json
```

---

## AI禁止行为清单

| 禁止行为 | 后果 |
|---------|------|
| ❌ 编写Python脚本执行翻译 | 翻译质量低，无法处理OCR错误 |
| ❌ 创建预置翻译词库 | 词库无法覆盖所有行业场景 |
| ❌ 用字符串替换替代翻译 | 无法理解上下文 |
| ❌ 验证时只是"浏览"而非运行脚本 | 无法保证质量 |
| ❌ 未询问用户选择方案直接开始 | 用户无法选择适合的方案 |

---

## AI必须执行的正确行为

| 行为 | 要求 |
|-----|------|
| ✅ 开场询问方案选择 | 必须问用户选方案一还是方案二 |
| ✅ 调度子代理并行翻译 | 读取manifest，分批调度子代理 |
| ✅ 记录翻译日志 | 每批完成后追加日志到step2_translate.log |
| ✅ 逐页验证质量 | 每页翻译后运行validate |
| ✅ 闭环验证 | chinese_count=0才算通过 |
| ✅ 断点续传 | 检查已存在文件，跳过已完成页 |

---

## 脚本职责边界

### 方案一脚本

| 脚本 | 职责 | 禁止 | 日志 |
|-----|------|------|------|
| scripts/step1_ocr.py | 逐页OCR识别 | ❌ 禁止翻译 | step1_ocr.log |
| scripts/step2_helper.py | 验证+合并 | ❌ 禁止翻译 | step2_translate.log |
| scripts/step3_build_word.py | 构建Word | ❌ 禁止翻译 | step3_build_word.log |
| scripts/step4_merge_word.py | 合并Word | ❌ 禁止翻译 | step4_merge.log |

### 方案二脚本

| 脚本 | 职责 | 禁止 | 日志 |
|-----|------|------|------|
| scripts/step1_ocr.py | 逐页OCR识别 | ❌ 禁止翻译 | step1_ocr.log |
| scripts/step2_md_helper.py | 验证Markdown | ❌ 禁止翻译 | step2_translate.log |
| scripts/step3_md_to_html.py | MD转HTML | ❌ 禁止翻译 | step3_build_word.log |
| scripts/step3_md_to_word.py | HTML→pandoc→Word | ❌ 禁止翻译 | step3_build_word.log |
| scripts/step4_merge_word.py | 合并Word | ❌ 禁止翻译 | step4_merge.log |

**只有AI能翻译，脚本永远不能翻译。**

---

## 参考文件

### 方案一
- `scripts/step1_ocr.py` - 阶段1：逐页OCR识别
- `scripts/step2_helper.py` - 阶段2辅助：验证和合并
- `scripts/step3_build_word.py` - 阶段3：构建Word文档
- `scripts/step4_merge_word.py` - 阶段4：合并多个Word文档

### 方案二
- `scripts/step1_ocr.py` - 阶段1：逐页OCR识别（同上）
- `scripts/step2_md_helper.py` - 阶段2辅助：验证Markdown翻译
- `scripts/step3_md_to_html.py` - 阶段3：Markdown转HTML（保留HTML表格）
- `scripts/step3_md_to_word.py` - 阶段3：HTML→pandoc→Word（使用reference.docx模板）
- `scripts/step4_merge_word.py` - 阶段4：合并多个Word文档（同上）
- `templates/reference.docx` - Word样式模板（Times New Roman 12pt）
