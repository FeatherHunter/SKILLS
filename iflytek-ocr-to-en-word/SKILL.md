---
name: ocr-to-en-word
description: 使用科大讯飞OCR将PDF手写体识别为Word文档，再翻译成英文版Word。当用户需要将PDF中文文档转换为英文Word时使用。支持手写体识别、分批翻译、避免上下文压缩。
---

# PDF手写体OCR识别 + 中文Word翻译英文版

## 核心功能

将PDF手写体中文文档 → Word文档 → 英文版Word文档

```
PDF(中文手写体) → 科大讯飞OCR → 中文Word → 分批翻译 → 英文Word
```

---

## 配置API密钥

> **首次使用需要配置，配置保存在 `.key` 文件中**

### 配置文件位置

```
{SKILL目录}/.key
```

### 配置格式

```json
{
  "APP_ID": "your_app_id",
  "API_SECRET": "your_api_secret",
  "API_KEY": "your_api_key"
}
```

### 配置方式

**直接告诉AI你的密钥：**

```
请配置科大讯飞OCR密钥：
APP_ID: your_app_id
API_SECRET: your_api_secret
API_KEY: your_api_key
```

AI会自动保存到 `.key` 文件。

### 获取密钥

1. 访问 [科大讯飞控制台](https://console.xfyun.cn/services/pdfOcr)
2. 创建应用，获取 APP_ID、API_SECRET、API_KEY
3. 提供给AI配置

### 密钥失败时

如果API调用失败（密钥过期、额度不足等），AI会交互式提醒：

```
⚠️ API调用失败，请提供新的密钥配置：
APP_ID: 
API_SECRET: 
API_KEY: 
```

---

## 工作流程

### 阶段1：PDF OCR识别

```
Step 1️⃣  上传PDF → 科大讯飞OCR服务
    ↓
Step 2️⃣  轮询状态 → 等待识别完成
    ↓
Step 3️⃣  下载Word → 获取中文Word文档
    ↓
Step 4️⃣  用户确认 → 检查识别质量
```

### 阶段2：分批翻译

```
Step 5️⃣  解压Word → 提取XML文件
    ↓
Step 6️⃣  提取中文 → 生成待翻译列表
    ↓
Step 7️⃣  分批翻译 → 每批100条，避免上下文压缩
    ↓
Step 8️⃣  应用翻译 → 替换XML中的中文
    ↓
Step 9️⃣  重新打包 → 生成英文版Word
```

---

## 避免上下文压缩策略

> **重要**: 翻译阶段采用分批处理，每批100条文本

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 提取所有中文文本到 texts_to_translate.json              │
│         (约700+条)                                              │
└────────────────────────────────┬────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 分批翻译，每批写入独立JSON文件                          │
│         translations_1.json (100条)                             │
│         translations_2.json (100条)                            │
│         ...                                                     │
└────────────────────────────────┬────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 合并所有翻译 → all_translations.json                    │
└────────────────────────────────┬────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: 应用翻译到XML文件 → 重新打包Word                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 方式1：告诉AI处理

```
使用 ocr-to-en-word 将 xxx.pdf 转换为英文Word
```

AI会自动完成：
1. 读取 `.key` 配置
2. 调用OCR识别
3. **分批翻译（AI作为翻译引擎，每批100条避免上下文压缩）**
4. 生成英文Word

### 方式2：AI交互式翻译

```
OCR识别完成后，AI会提取中文文本并分批翻译：

阶段1: PDF → 中文Word（科大讯飞OCR）
阶段2: 中文Word → 提取中文文本（~700条）
阶段3: 分批翻译（translations_1.json, translations_2.json...）
阶段4: 合并应用 → 英文Word
```

AI在翻译阶段会：
- 每批100条独立翻译
- 写入独立JSON文件避免上下文压缩
- 合并后应用到Word

### 方式3：命令行

```bash
# 一键完成
python scripts/ocr_translate.py input.pdf -o output_en.docx

# 仅翻译已有Word
python scripts/translate_to_en.py input.docx --extract
python scripts/translate_to_en.py input.docx --apply translations.json -o output_en.docx
```

---

## Word文档结构

`.docx` 本质是ZIP压缩包：

```
document.docx
├── word/document.xml       # 主文档内容 (翻译这里)
├── word/header*.xml        # 页眉 (翻译这里)
├── word/footer*.xml        # 页脚 (翻译这里)
├── word/styles.xml         # 样式 (不翻译)
└── word/media/             # 图片 (不翻译)
```

### 翻译规则

- 翻译 `<w:t>` 标签内的文本
- 不翻译XML标签名、属性名
- 不翻译技术标识符（文件编号、代码等）

---

## 相关链接

- [科大讯飞开放平台](https://www.xfyun.cn/)
- [OCR服务控制台](https://console.xfyun.cn/services/pdfOcr)
- [API文档](https://www.xfyun.cn/doc/words/OCRforLLM/skill.html)

---

## 文件结构

```
iflytek-ocr-to-en-word/
├── SKILL.md                         # 本文件
├── .key                             # API密钥配置
├── scripts/
│   ├── ocr_translate.py             # 一键完成（复用下方官方OCR）
│   └── translate_to_en.py           # Word翻译脚本
└── ocr-skill/                       # 科大讯飞官方OCR脚本
    ├── scripts/
    │   ├── image_ocr.py
    │   └── pdf_ocr.py               # 官方实现，被 ocr_translate.py import
    └── SKILL.md
```
