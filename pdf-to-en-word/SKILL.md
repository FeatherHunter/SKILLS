---
name: pdf-to-en-word
description: PDF扫描件（含图片）转英文Word文档技能。支持内容识别、横版处理、中文翻译英文、手动构建docx，保持表格结构和格式布局。
trigger:
  - "图片转word"
  - "图片转docx"
  - "扫描件转文档"
  - "PDF扫描转Word"
  - "图片识别转Word"
  - "多页PDF转Word"
  - "PDF转英文Word"
  - "扫描件翻译转Word"
---

# pdf-to-en-word PDF转英文Word文档技能

## 技能概述

本技能提供从PDF扫描件/图片到英文Word文档（docx格式）的完整转换流程。核心流程：

```
PDF/图片 → 内容识别 → 中文翻译英文 → 构建英文Word文档
```

## 适用场景

- 将扫描版PDF/图片转换为可编辑英文Word文档
- 保持原有表格结构和格式布局
- 中文翻译为英文（国际注册标准需求）
- 对转换精度有严格要求（手动控制每个元素）

## 核心流程

**必经阶段**：第一阶段（图片内容识别）→ 第三阶段（中文翻译英文）→ 第四阶段（构建Word文档）

**可选阶段**：第二阶段（HTML原型）用于可视化预览

**文档类型分流**：

```
┌──────────────────────────────────────────────────┐
│                 输入图片/PDF                      │
└────────────────────┬─────────────────────────────┘
                     │
              ┌──────┴──────┐
              │ 单页？多页？ │
              └──┬───────┬──┘
                 │       │
          单页   │       │  多页
                 ▼       ▼
       直接执行阶段1→3→4    逐页子任务 + 合并组装
```

### 单页文档流程

直接按阶段1→3→4执行（跳过可选的阶段2）。

### 多页文档流程

**问题**：多页文档在单个会话中处理会导致上下文污染，后续页面质量下降。

**解决方案：独立子任务逐页处理 + XML片段合并组装**

```
主会话（协调调度，不处理具体内容）
   │
   │  1. 将PDF拆分为单页图片
   │
   │  2. 并行派发所有子任务：
   ├──> 子任务1：Read图片 → 识别+翻译+生成XML → Write到文件 → 返回元数据摘要
   ├──> 子任务2：Read图片 → 识别+翻译+生成XML → Write到文件 → 返回元数据摘要
   ├──> 子任务3：Read图片 → 识别+翻译+生成XML → Write到文件 → 返回元数据摘要
   └──> ...
   （所有子任务并行执行，术语表统一传入）
   
   3. 脚本合并所有XML文件 → 组装为单个document.xml
   4. ZIP打包为最终docx
```

**关键规则**：
- **主代理禁止读取图片内容**：主代理只负责拆分PDF获取路径、调度子任务、合并结果，绝不能自己Read图片（会导致上下文过大被压缩）
- 每页使用独立子任务（Agent），子任务自行Read图片，零上下文污染
- 每个独立子任务只处理1张图片，将XML写入文件后返回元数据摘要
- 每页独立推断自己的样式（字号、字体、边框等）
- 不共享样式：PDF可能前后页样式不一致，各自处理最准确
- 每页独立翻译，翻译一致性靠术语表保证（见下方机制）
- 每页之间用 `<w:br w:type="page"/>` 分页
- 最后统一组装为单个document.xml

**主代理调度流程**：
```
1. 拆分PDF → 得到图片路径列表 [page_1.png, page_2.png, ...]
   （此步骤不读取图片内容，只获取文件路径）

2. 创建临时目录 temp/ 存放中间文件

3. 并行派发所有子任务（Task工具），每个子任务传入图片路径+术语表（如有）：
   子任务1 Prompt: "图片路径: D:\...\page_1.png, 输出文件: temp/page_1.xml" + 术语表 + 子任务Prompt模板
   子任务2 Prompt: "图片路径: D:\...\page_2.png, 输出文件: temp/page_2.xml" + 术语表 + 子任务Prompt模板
   ...
   （所有子任务并行启动，每个子任务独立Read图片，写入文件，返回元数据摘要）
   ...
   （子任务自行用Read工具读取图片，将XML片段写入文件，只返回元数据摘要）

4. 主代理只接收子任务返回的元数据摘要：
   例如：{"tables": 2, "paragraphs": 5, "file": "temp/page_1.xml"}
   （XML内容在文件中，不进入主代理上下文）

5. 执行轻量验证（文件完整性、异常检测）

6. 调用合并脚本组装document.xml并ZIP打包
```

**子任务返回规则（必须遵守）**：
- 子任务必须将完整XML内容写入指定的输出文件（用Write工具）
- 子任务只返回精简元数据摘要，格式如下：
  ```
  页面: X
  表格数量: X
  表格1: X行X列
  表格2: X行X列
  段落数量: X
  输出文件: temp/page_X.xml
  ```
- 禁止在返回中包含XML内容（避免主代理上下文膨胀）

**术语一致性机制**：
```
术语表由用户提供，不由AI自动生成。

规则：
1. 用户在启动任务时提供术语表文件（如有），格式为JSON：
   例如：{ "四环素": "Tetracycline", "胶囊": "Capsule", "批号": "Batch No." }

2. 如用户未提供术语表，则无术语表，AI自由翻译，只需符合医药领域专业标准

3. 术语表在所有子任务中统一传入，所有页面遵循相同翻译

4. 子任务不再返回术语信息，不动态积累术语表
```

**交叉验证步骤**：

子代理在写完XML文件后，自行执行内容验证（因为它同时拥有图片和刚生成的XML）：

```
子代理验证清单（在返回摘要前执行）：
注意：验证使用内存中已加载的图片和刚生成的XML，禁止重新Read文件

1. 对照图片检查XML内容：
   - 所有文字内容是否已包含（逐段对照）
   - 表格行列数是否与图片一致
   - 数字、日期、批号是否精确复制（非翻译）
2. 元数据自洽：
   - 统计的表格数与实际<w:tbl>标签数一致
   - 统计的段落数与实际<w:p>标签数一致
3. XML格式检查：
   - 所有标签正确闭合
   - 命名空间声明存在
4. 如发现问题，修正后重新写入文件
```

主代理验证（仅基于元数据摘要，轻量级）：

```
1. 文件完整性：确认所有temp/page_X.xml文件均已生成
2. 异常检测：如某页段落数=0且表格数=0，重新处理该页
3. 失败重试：如某页子任务失败或文件未生成，重新派发该页子任务
```

最终验证：用户在Word中打开docx，对照原始PDF检查

**合并组装过程**：

主代理创建合并脚本并执行，避免XML内容进入上下文：

```javascript
// merge_and_pack.js - 合并XML文件并打包为docx
const fs = require('fs');
const path = require('path');
const archiver = require('archiver');

// 1. 合并所有页面XML片段
const tempDir = './temp';
const pages = fs.readdirSync(tempDir)
  .filter(f => f.match(/^page_\d+\.xml$/))
  .sort((a, b) => {
    const numA = parseInt(a.match(/\d+/)[0]);
    const numB = parseInt(b.match(/\d+/)[0]);
    return numA - numB;
  });

const xmlParts = pages.map(p => fs.readFileSync(path.join(tempDir, p), 'utf8'));
const content = xmlParts.join('\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n');

const documentXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    ${content}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/>
    </w:sectPr>
  </w:body>
</w:document>`;

// 2. 创建目录结构
fs.mkdirSync('./word/_rels', { recursive: true });
fs.mkdirSync('./_rels', { recursive: true });
fs.mkdirSync('./docProps', { recursive: true });
fs.writeFileSync('./word/document.xml', documentXml);

// 3. 写入其他必需XML文件（从附录1模板复制）
fs.writeFileSync('./word/styles.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:docDefaults>
        <w:rPrDefault>
            <w:rPr>
                <w:rFonts w:ascii="Calibri" w:eastAsia="SimSun" w:hAnsi="Calibri" w:cs="Times New Roman"/>
                <w:sz w:val="24"/>
                <w:szCs w:val="24"/>
            </w:rPr>
        </w:rPrDefault>
    </w:docDefaults>
    <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
        <w:name w:val="Normal"/>
    </w:style>
    <w:style w:type="table" w:styleId="TableGrid">
        <w:name w:val="Table Grid"/>
        <w:tblPr>
            <w:tblBorders>
                <w:top w:val="single" w:sz="4" w:color="000000"/>
                <w:left w:val="single" w:sz="4" w:color="000000"/>
                <w:bottom w:val="single" w:sz="4" w:color="000000"/>
                <w:right w:val="single" w:sz="4" w:color="000000"/>
                <w:insideH w:val="single" w:sz="4" w:color="000000"/>
                <w:insideV w:val="single" w:sz="4" w:color="000000"/>
            </w:tblBorders>
        </w:tblPr>
    </w:style>
</w:styles>`);

fs.writeFileSync('./word/settings.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:zoom w:percent="100"/>
    <w:defaultTabStop w:val="720"/>
    <w:characterSpacingControl w:val="doNotCompress"/>
    <w:compat>
        <w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/>
    </w:compat>
</w:settings>`);

fs.writeFileSync('./word/fontTable.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:fonts xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:font w:name="Calibri"><w:panose1 w:val="020F0502020204030204"/><w:charset w:val="00"/></w:font>
    <w:font w:name="SimSun"><w:panose1 w:val="02010600040101010101"/><w:charset w:val="86"/></w:font>
    <w:font w:name="Times New Roman"><w:panose1 w:val="02020603050405020304"/><w:charset w:val="00"/></w:font>
</w:fonts>`);

fs.writeFileSync('./word/_rels/document.xml.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
    <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>
</Relationships>`);

fs.writeFileSync('./[Content_Types].xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
    <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
    <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
    <Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>
    <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
    <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats.extended-properties+xml"/>
</Types>`);

fs.writeFileSync('./_rels/.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
    <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>`);

fs.writeFileSync('./docProps/core.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <dc:title>Converted Document</dc:title>
    <dc:creator>PDF-to-Word Converter</dc:creator>
    <cp:revision>1</cp:revision>
    <dcterms:created xsi:type="dcterms:W3CDTF">${new Date().toISOString()}</dcterms:created>
    <dcterms:modified xsi:type="dcterms:W3CDTF">${new Date().toISOString()}</dcterms:modified>
</cp:coreProperties>`);

fs.writeFileSync('./docProps/app.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
    <Template>Normal.dotm</Template>
    <TotalTime>0</TotalTime>
    <Application>Microsoft Office Word</Application>
    <DocSecurity>0</DocSecurity>
    <AppVersion>16.0000</AppVersion>
</Properties>`);

// 4. ZIP打包为docx
const output = fs.createWriteStream('./output.docx');
const archive = archiver('zip', { zlib: { level: 9 } });
archive.pipe(output);

// 关系文件不压缩
archive.file('./[Content_Types].xml', { name: '[Content_Types].xml', store: true });
archive.file('./_rels/.rels', { name: '_rels/.rels', store: true });
archive.file('./word/_rels/document.xml.rels', { name: 'word/_rels/document.xml.rels', store: true });

// 其他XML文件压缩
archive.file('./word/document.xml', { name: 'word/document.xml' });
archive.file('./word/styles.xml', { name: 'word/styles.xml' });
archive.file('./word/settings.xml', { name: 'word/settings.xml' });
archive.file('./word/fontTable.xml', { name: 'word/fontTable.xml' });
archive.file('./docProps/core.xml', { name: 'docProps/core.xml' });
archive.file('./docProps/app.xml', { name: 'docProps/app.xml' });

archive.finalize();
```

主代理执行方式：
```bash
node merge_and_pack.js
# 输出 output.docx
```

关键原则：
- XML片段通过文件传递，不进入主代理上下文
- 合并和打包操作用脚本完成，主代理只执行脚本命令
- 主代理上下文仅包含：图片路径列表、元数据摘要、术语表
```

**子任务Prompt模板**：
```
你是一个文档转换助手。请将以下图片中的内容转换为英文OOXML格式。

处理流程：
1. 识别内容：文字、表格、布局
   - 无法识别的手写内容用[?]标注
2. 检测方向：如宽>高，先旋转为竖版
3. 推断样式：根据视觉特征判断格式
   - 字号：大且加粗/居中→标题(16-18pt)，中等→正文(11-12pt)，较小且在表格内→表格(10pt)，最小/灰色/底部→注释(9pt)
   - 对齐：观察原文对齐方式（居中/左对齐/右对齐），用<w:jc>还原
   - 加粗：原文加粗部分用<w:b/>标记
   - 颜色：非黑色文字用<w:color w:val="RRGGBB"/>还原
   - 行间距：根据视觉间距用<w:spacing w:line="X"/>还原
   - 缩进：首行缩进用<w:ind w:firstLineChars="200"/>（约2字符）
   - 表格列宽：根据图片中各列视觉宽度比例，用<w:gridCol>设置相对宽度
   - 表格边框：单线1pt黑色，如有特殊边框样式（双线、粗线）需还原
   - 单元格背景：灰色/彩色背景用<w:shd w:fill="RRGGBB"/>还原
4. 翻译英文：将所有中文内容翻译为英文
   - 关键数据精确复制，禁止翻译：数字、日期、批号、有效期、剂量、规格
   - 专业术语翻译准确，符合医药领域标准
   - 遵循术语表中的翻译（如有术语表）
   - 如无术语表，自由翻译，保持医药领域专业性
5. 生成XML：先生成完整XML内容，再根据XML统计元数据

样式规则：
- 字体：英文Calibri，中文宋体(SimSun)
- 字号：标题16-18pt，正文11-12pt，表格10pt，注释9pt
- 表格边框：单线1pt黑色
- 横版原则：不拆分表格，保持结构完整
- 含空格的文本必须加 xml:space="preserve"（如填空线、缩进）

输出要求（必须遵守）：

1. 使用Write工具将完整XML内容写入指定的输出文件

2. 返回精简元数据摘要（禁止返回XML内容）：

## 页面元数据摘要
- 页面：X
- 表格数量：X
- 表格1：X行X列
- 表格2：X行X列
- 段落数量：X
- 输出文件：{output_file}

注意：
- 先生成完整XML内容，再根据XML统计元数据（确保一致）
- 不要遗漏任何内容
- 只输出内容部分，不要输出<w:document>、<w:body>、<w:sectPr>等外层结构
- 使用正确的WordprocessingML命名空间 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
- 所有XML标签必须正确闭合
- **必须将完整XML内容用Write工具写入输出文件：{output_file}**
- **写完文件后，自行验证内容完整性（对照图片检查是否遗漏）**
- **返回时只返回精简元数据摘要，禁止返回XML内容**

图片路径：{page_image}
（请使用Read工具读取上述图片路径，读取后再进行处理）

输出文件：{output_file}
（请将生成的XML内容片段写入此文件，写完后自行验证内容完整性）

术语表（用户提供，如无则留空）：
{terminology}
```

### 第一阶段：图片内容识别

**目标**：准确提取图片中的文字、表格、布局信息

**方法论**：
1. **视觉结构分析**
   - 识别文档类型（表单、报告、日志等）
   - 分析布局层次（标题、正文、表格、页眉页脚）
   - 确定关键信息区域

2. **内容提取原则**
   - 对于印刷体：直接读取文字内容
   - 对于手写体：根据上下文合理推测，不确定处标注[?]
   - 表格：识别行列结构、单元格合并、背景色、边框样式
    - **页眉页脚识别**：
      - 页眉：每页顶部重复出现的公司名、文档标题、Logo等
      - 页脚：每页底部重复出现的页码、日期、版本号等
      - 处理方式：作为普通段落放在页面内容顶部/底部，字号用9pt
   - **非文字内容识别**：
     - 印章/签名：用[SEAL: XXX]、[SIGNATURE]标注位置
     - Logo：用[LOGO]标注位置
     - 流程图/化学式：用[DIAGRAM]标注，描述内容
   - **字号推断**：根据视觉大小判断文字级别
     - 大且加粗/居中 → 标题级别（16-18pt）
     - 中等大小 → 正文级别（11-12pt）
     - 较小且在表格内 → 表格内容级别（10pt）
     - 最小、灰色或底部 → 注释级别（9pt）

3. **交互确认策略**（灵活执行，非强制）
   - 关键信息（姓名、日期、数字）向用户确认
   - 模糊内容提供选项让用户选择处理方式
   - 确认格式偏好（手写风格 vs 标准印刷体）
   - *注：如用户明确要求"自由发挥/合理推测"，则可跳过确认直接处理*

4. **横版页面处理**
   - **检测**：识别图片方向（宽>高为横版）
   - **旋转**：横版图片旋转90°为竖版
   - **原则**：不拆分表格，保持原有结构完整
     - 原横版内容放得下一页，旋转后同样放得下
     - 表格变长但结构不变，Word自动换行
     - 内容完整性优先于美观度

**输出**：结构化内容数据（可存储为JSON或中间格式）

### 第二阶段：HTML原型构建（可选）

**目标**：创建可视化HTML，作为Word文档的"设计稿"（如只需快速生成Word可跳过此阶段）

**方法论**：
1. **页面规格设定**
   - 使用CSS `@page` 规则设置A4尺寸（210mm × 297mm）
   - 设置页边距（通常15-20mm）
   - 背景色模拟打印预览效果

2. **结构还原策略**
   - **文本块**：使用语义化HTML标签（h1-h6, p, span）
    - **表格**：使用`<table>`，设置固定列宽（单位mm），确保行列数与图片一致
   - **表单元素**：使用flex/grid布局还原填写区域
   - **下划线/填写线**：使用border-bottom或text-decoration

3. **样式控制原则**
    - 使用绝对单位（mm, pt）而非相对单位（px, em）
    - 字体选择：中文用宋体，英文用Calibri（最规范的Word文档字体）
    - 字号推断：根据图片中文字的视觉大小自动推断
      - 标题：视觉较大、加粗、居中 → 16-18pt
      - 正文：中等大小、常规字体 → 11-12pt
      - 表格内容：较小、紧凑 → 10pt
      - 注释/脚注：最小 → 9pt

**输出**：单文件HTML，可在浏览器预览，视觉效果与图片一致

### 第三阶段：中文翻译英文

**目标**：将中文内容翻译为英文（国际注册标准需求）

**核心原则**：
1. **关键数据精确复制，禁止翻译**：
   - 数字、日期、批号、有效期、剂量、规格、百分比
   - 化学式、分子式、代码、编号
   - 这些数据必须与原文完全一致，包括格式

2. **专业翻译**：
   - 使用LLM进行上下文感知翻译
   - 术语翻译准确，遵循术语表（如有）
   - 不确定的术语保留原文并括号标注英文

**方法论**：
1. **LLM动态翻译**（推荐方案）
   - 直接使用LLM进行上下文感知翻译
   - 专业术语由LLM根据上下文自动判断翻译
   - 通过术语表保证多页一致性
   - 实现示例见【技术附录：LLM翻译方案】

2. **布局适配**
   - 英文通常比中文长，需调整列宽
   - 使用自适应列宽：`<w:tcW w:w="0" w:type="auto"/>`
   - 减小字体大小（英文10pt通常足够）
   - 保持原有对齐方式

**输出**：翻译后的内容数据

### 第四阶段：手动构建Word文档

**目标**：从零构建符合OOXML规范的docx文件

**核心原理**：
```
docx文件 = ZIP压缩包(
    [Content_Types].xml    ← 文件类型声明
    _rels/.rels           ← 包级关系定义
    word/
        document.xml      ← 核心文档内容（重点）
        styles.xml        ← 样式定义
        settings.xml      ← 文档设置
        fontTable.xml     ← 字体映射
        _rels/document.xml.rels  ← 文档级关系
    docProps/
        core.xml          ← 元数据（标题、作者）
        app.xml           ← 应用程序属性
)
```

**构建步骤**：

1. **创建目录结构**
   ```
   temp/
   ├── [Content_Types].xml
   ├── _rels/
   │   └── .rels
   ├── word/
   │   ├── _rels/
   │   │   └── document.xml.rels
   │   ├── document.xml
   │   ├── styles.xml
   │   ├── settings.xml
   │   └── fontTable.xml
   └── docProps/
       ├── core.xml
       └── app.xml
   ```

2. **编写核心XML文件**
   - 见【技术附录：XML文件模板】获取各文件完整内容
   - **document.xml**：使用WordprocessingML语言描述内容
   - **styles.xml**：定义文档样式（必须）
   - **其他文件**：使用标准模板，修改元数据即可

3. **打包为ZIP**
   - 见【技术附录：ZIP打包方案】
   - 关键要求：关系文件（.rels）不压缩，其他XML文件DEFLATE压缩
   - 文件扩展名改为`.docx`
   - **关键**：保持UTF-8编码

**OOXML关键元素速查**：

| 元素 | 用途 | 示例 | 父元素 |
|------|------|------|--------|
| `<w:document>` | 根元素 | 包含整个文档 | - |
| `<w:body>` | 文档主体 | 包含段落和表格 | `<w:document>` |
| `<w:p>` | 段落 | 文本块、表格单元格内容 | `<w:body>`, `<w:tc>` |
| `<w:r>` | 文本运行 | 统一格式的文本片段 | `<w:p>` |
| `<w:rPr>` | 文本属性 | 字体、字号、加粗 | `<w:r>` |
| `<w:t>` | 文本内容 | 实际显示的文字 | `<w:r>` |
| `<w:tbl>` | 表格 | 数据表格容器 | `<w:body>` |
| `<w:tr>` | 表格行 | 表格的一行 | `<w:tbl>` |
| `<w:tc>` | 表格单元格 | 行内的单元格 | `<w:tr>` |
| `<w:tcPr>` | 单元格属性 | 宽度、背景色 | `<w:tc>` |
| `<w:jc>` | 对齐方式 | left/center/right | `<w:pPr>` |
| `<w:b>` | 加粗 | 粗体文本 | `<w:rPr>` |
| `<w:u>` | 下划线 | single/double | `<w:rPr>` |
| `<w:sz>` | 字号 | 以半点为单位（24=12pt） | `<w:rPr>` |
| `<w:color>` | 文字颜色 | `<w:color w:val="FF0000"/>` 红色 | `<w:rPr>` |
| `<w:spacing>` | 行间距 | `<w:spacing w:line="360"/>` 1.5倍行距 | `<w:pPr>` |
| `<w:ind>` | 缩进 | `<w:ind w:firstLineChars="200"/>` 首行缩进2字符 | `<w:pPr>` |
| `<w:shd>` | 背景/阴影 | `<w:shd w:fill="CCCCCC"/>` 灰色背景 | `<w:tcPr>` |
| `<w:tblBorders>` | 表格边框 | 定义所有边框 | `<w:tblPr>` |
| `<w:gridCol>` | 列宽定义 | `<w:gridCol w:w="2000"/>` | `<w:tblGrid>` |
| `<w:gridSpan>` | 水平合并 | 跨列数（gridSpan=2表示合并2列） | `<w:tcPr>` |
| `<w:vMerge>` | 垂直合并 | restart=起始单元格，无val=续接单元格 | `<w:tcPr>` |
| `<w:sectPr>` | 节属性 | 页面大小、边距、分节 | `<w:body>` |

**常用属性值速查**：

| 属性 | 值 | 说明 |
|------|-----|------|
| 行间距 `w:line` | 240 | 单倍行距（12pt） |
| 行间距 `w:line` | 360 | 1.5倍行距 |
| 行间距 `w:line` | 480 | 双倍行距 |
| 首行缩进 `w:firstLineChars` | 200 | 约2字符（200/100=2） |
| 颜色 `w:val` | 000000 | 黑色 |
| 颜色 `w:val` | FF0000 | 红色 |
| 颜色 `w:val` | 0000FF | 蓝色 |
| 颜色 `w:val` | CCCCCC | 浅灰色 |
| 颜色 `w:val` | FFFF00 | 黄色（高亮） |

## 技术附录

### 附录1：XML文件完整模板

#### 1. [Content_Types].xml（文件类型声明）
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
    <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
    <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
    <Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>
    <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
    <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
```

#### 2. _rels/.rels（包级关系）
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
    <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
```

#### 3. word/_rels/document.xml.rels（文档级关系）
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
    <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>
</Relationships>
```

#### 4. word/styles.xml（样式定义）
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:docDefaults>
        <w:rPrDefault>
            <w:rPr>
                <w:rFonts w:ascii="Calibri" w:eastAsia="SimSun" w:hAnsi="Calibri" w:cs="Times New Roman"/>
                <w:sz w:val="24"/>
                <w:szCs w:val="24"/>
            </w:rPr>
        </w:rPrDefault>
    </w:docDefaults>
    <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
        <w:name w:val="Normal"/>
    </w:style>
    <w:style w:type="table" w:styleId="TableGrid">
        <w:name w:val="Table Grid"/>
        <w:tblPr>
            <w:tblBorders>
                <w:top w:val="single" w:sz="4" w:color="000000"/>
                <w:left w:val="single" w:sz="4" w:color="000000"/>
                <w:bottom w:val="single" w:sz="4" w:color="000000"/>
                <w:right w:val="single" w:sz="4" w:color="000000"/>
                <w:insideH w:val="single" w:sz="4" w:color="000000"/>
                <w:insideV w:val="single" w:sz="4" w:color="000000"/>
            </w:tblBorders>
        </w:tblPr>
    </w:style>
</w:styles>
```

#### 5. word/settings.xml（文档设置）
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:zoom w:percent="100"/>
    <w:defaultTabStop w:val="720"/>
    <w:characterSpacingControl w:val="doNotCompress"/>
    <w:compat>
        <w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/>
    </w:compat>
</w:settings>
```

#### 6. word/fontTable.xml（字体表）
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:fonts xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:font w:name="Calibri">
        <w:panose1 w:val="020F0502020204030204"/>
        <w:charset w:val="00"/>
    </w:font>
    <w:font w:name="SimSun">
        <w:panose1 w:val="02010600040101010101"/>
        <w:charset w:val="86"/>
    </w:font>
    <w:font w:name="Times New Roman">
        <w:panose1 w:val="02020603050405020304"/>
        <w:charset w:val="00"/>
    </w:font>
</w:fonts>
```

#### 7. docProps/core.xml（核心属性）
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties 
    xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <dc:title><!-- 文档标题 --></dc:title>
    <dc:subject><!-- 主题 --></dc:subject>
    <dc:creator><!-- 创建者 --></dc:creator>
    <cp:lastModifiedBy><!-- 最后修改者 --></cp:lastModifiedBy>
    <cp:revision>1</cp:revision>
    <dcterms:created xsi:type="dcterms:W3CDTF">2025-01-01T00:00:00Z</dcterms:created>
    <dcterms:modified xsi:type="dcterms:W3CDTF">2025-01-01T00:00:00Z</dcterms:modified>
</cp:coreProperties>
```

#### 8. docProps/app.xml（应用属性）
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
    <Template>Normal.dotm</Template>
    <TotalTime>0</TotalTime>
    <Pages>1</Pages>
    <Words>0</Words>
    <Characters>0</Characters>
    <Application>Microsoft Office Word</Application>
    <DocSecurity>0</DocSecurity>
    <Lines>0</Lines>
    <Paragraphs>0</Paragraphs>
    <AppVersion>16.0000</AppVersion>
</Properties>
```

### 附录2：document.xml结构参考

**基础结构模板**：
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document 
    xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <w:body>
        <!-- 在这里插入内容：段落、表格等 -->
        
        <w:sectPr>
            <w:pgSz w:w="11906" w:h="16838"/>
            <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" 
                     w:header="720" w:footer="720" w:gutter="0"/>
        </w:sectPr>
    </w:body>
</w:document>
```

**段落结构**：
```xml
<w:p>
    <w:pPr>
        <w:jc w:val="center"/>  <!-- 居中对齐，可选 -->
    </w:pPr>
    <w:r>
        <w:rPr>
            <w:b/>  <!-- 加粗，可选 -->
            <w:sz w:val="24"/>  <!-- 字号12pt，可选 -->
        </w:rPr>
        <w:t>段落文本内容</w:t>
    </w:r>
</w:p>
```

**带下划线的文本（用于表单填写线）**：
```xml
<w:r>
    <w:rPr>
        <w:u w:val="single"/>
    </w:rPr>
    <w:t xml:space="preserve"> 填写内容 </w:t>
</w:r>
```

**表格结构**：
```xml
<w:tbl>
    <w:tblPr>
        <w:tblStyle w:val="TableGrid"/>
        <w:tblW w:w="9000" w:type="dxa"/>
        <!-- 边框定义（可选，也可在styles.xml中定义） -->
        <w:tblBorders>
            <w:top w:val="single" w:sz="4" w:color="000000"/>
            <w:left w:val="single" w:sz="4" w:color="000000"/>
            <w:bottom w:val="single" w:sz="4" w:color="000000"/>
            <w:right w:val="single" w:sz="4" w:color="000000"/>
            <w:insideH w:val="single" w:sz="4" w:color="000000"/>
            <w:insideV w:val="single" w:sz="4" w:color="000000"/>
        </w:tblBorders>
    </w:tblPr>
    <w:tblGrid>
        <!-- 定义列宽，单位：twips -->
        <w:gridCol w:w="1000"/>
        <w:gridCol w:w="1000"/>
        <!-- 更多列... -->
    </w:tblGrid>
    <!-- 表头行 -->
    <w:tr>
        <w:tc>
            <w:tcPr>
                <w:tcW w:w="1000" w:type="dxa"/>
                <w:vAlign w:val="center"/>
            </w:tcPr>
            <w:p>
                <w:pPr>
                    <w:jc w:val="center"/>
                </w:pPr>
                <w:r>
                    <w:rPr>
                        <w:b/>
                    </w:rPr>
                    <w:t>列标题</w:t>
                </w:r>
            </w:p>
        </w:tc>
        <!-- 更多单元格... -->
    </w:tr>
    <!-- 数据行... -->
</w:tbl>
```

### 附录3：多页文档与合并单元格

#### 多页文档处理

当源图片包含多页时，使用分页符分隔：

```xml
<w:body>
    <!-- 第一页内容 -->
    <w:p>...</w:p>
    <w:tbl>...</w:tbl>
    <w:p>
        <w:r>
            <w:br w:type="page"/>  <!-- 分页符 -->
        </w:r>
    </w:p>
    <!-- 第二页内容 -->
    <w:p>...</w:p>
    <w:tbl>...</w:tbl>
    
    <!-- 最后一个sectPr（必须） -->
    <w:sectPr>
        <w:pgSz w:w="11906" w:h="16838"/>
        <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/>
    </w:sectPr>
</w:body>
```

**关键**：`<w:sectPr>` 只能出现在 `<w:body>` 的最后。多页用 `<w:br w:type="page"/>` 分页即可。

#### 合并单元格处理

**跨列合并**（水平合并）：
```xml
<w:tc>
    <w:tcPr>
        <w:gridSpan w:val="2"/>  <!-- 合并2列 -->
    </w:tcPr>
    <w:p><w:r><w:t>跨2列的内容</w:t></w:r></w:p>
</w:tc>
```

**跨行合并**（垂直合并）：
```xml
<!-- 第一行：合并起始 -->
<w:tc>
    <w:tcPr>
        <w:vMerge w:val="restart"/>
    </w:tcPr>
    <w:p><w:r><w:t>合并内容</w:t></w:r></w:p>
</w:tc>
<!-- 第二行：续接 -->
<w:tc>
    <w:tcPr>
        <w:vMerge/>  <!-- 无val，表示续接上方 -->
    </w:tcPr>
    <w:p/>
</w:tc>
```

*注：以上为基础模板，实际使用时根据内容需求灵活调整。非表格内容可删除表格部分，非必填字段可删除对应元素。*

### 附录4：ZIP打包方案

docx本质是ZIP压缩包，将XML文件按目录结构打包即可。

**打包规则**：
- 关系文件（.rels）和[Content_Types].xml**不压缩**（存储模式）
- 其他XML文件使用**DEFLATE压缩**
- 文件扩展名改为`.docx`

**方案一：命令行（最简单）**
```bash
# 在temp/目录下打包
cd temp && zip -r -0 -X ../output.docx "[Content_Types].xml" _rels word docProps
# -0: 不压缩（如需混合压缩，分步处理）
# -X: 排除系统隐藏文件
```

**方案二：Node.js（推荐）**
```javascript
const archiver = require('archiver');
const fs = require('fs');

const output = fs.createWriteStream('output.docx');
const archive = archiver('zip', { zlib: { level: 9 } });

archive.pipe(output);

// 关系文件不压缩
archive.file('temp/[Content_Types].xml', { name: '[Content_Types].xml', store: true });
archive.file('temp/_rels/.rels', { name: '_rels/.rels', store: true });
archive.file('temp/word/_rels/document.xml.rels', { name: 'word/_rels/document.xml.rels', store: true });

// 其他XML文件压缩
archive.file('temp/word/document.xml', { name: 'word/document.xml' });
archive.file('temp/word/styles.xml', { name: 'word/styles.xml' });
archive.file('temp/word/settings.xml', { name: 'word/settings.xml' });
archive.file('temp/word/fontTable.xml', { name: 'word/fontTable.xml' });
archive.file('temp/docProps/core.xml', { name: 'docProps/core.xml' });
archive.file('temp/docProps/app.xml', { name: 'docProps/app.xml' });

archive.finalize();
```

**方案三：Python**
```python
import zipfile

with zipfile.ZipFile('output.docx', 'w', zipfile.ZIP_DEFLATED) as zf:
    # 关系文件不压缩
    zf.write('temp/[Content_Types].xml', '[Content_Types].xml', compress_type=zipfile.ZIP_STORED)
    zf.write('temp/_rels/.rels', '_rels/.rels', compress_type=zipfile.ZIP_STORED)
    # 其他XML文件压缩
    zf.write('temp/word/document.xml', 'word/document.xml')
    zf.write('temp/word/styles.xml', 'word/styles.xml')
    # ... 其余文件
```

*注：推荐使用现成的ZIP库，无需手动拼二进制。核心是保持目录结构正确、关系文件不压缩。*

### 附录5：单位转换工具

**长度单位转换（mm → twips）**：
- 1 英寸 = 1440 twips
- 1 mm = 56.7 twips（约57）
- A4宽度 210mm = 11906 twips
- A4高度 297mm = 16838 twips
- 1cm边距 = 567 twips
- 1mm边距 = 57 twips（约）

**字号单位转换（pt → half-points）**：
- `<w:sz>` 标签使用半点单位
- 12pt = 24 half-points
- 11pt = 22 half-points
- 10pt = 20 half-points
- 18pt = 36 half-points

**转换公式**：
```javascript
// mm to twips
const twips = Math.round(mm * 1440 / 25.4);

// pt to half-points
const halfPoints = pt * 2;
```

### 附录6：命名空间速查表

| 前缀 | 命名空间URL | 用途 |
|------|-------------|------|
| `w` | `http://schemas.openxmlformats.org/wordprocessingml/2006/main` | 核心WordprocessingML元素 |
| `r` | `http://schemas.openxmlformats.org/officeDocument/2006/relationships` | 关系（用于关联样式、字体等）|
| `cp` | `http://schemas.openxmlformats.org/package/2006/metadata/core-properties` | 核心属性（标题、作者等）|
| `dc` | `http://purl.org/dc/elements/1.1/` | Dublin Core元数据 |
| `dcterms` | `http://purl.org/dc/terms/` | Dublin Core术语 |
| (无) | `http://schemas.openxmlformats.org/package/2006/content-types` | [Content_Types].xml根命名空间 |
| (无) | `http://schemas.openxmlformats.org/package/2006/relationships` | .rels文件根命名空间 |
| (无) | `http://schemas.openxmlformats.org/officeDocument/2006/extended-properties` | app.xml根命名空间 |

### 附录7：LLM动态翻译方案

**核心思路**：直接调用LLM进行翻译，无需维护硬编码术语表

**翻译Prompt模板**：

```
你是一个专业的文档翻译助手。请将以下中文内容翻译为英文。

核心原则：
1. 关键数据精确复制，禁止翻译：数字、日期、批号、有效期、剂量、规格、百分比、化学式
2. 专业术语翻译准确，不确定时保留原文并括号标注英文
3. 保持原有的格式和标点
4. 遵循术语表中的翻译（如有）

术语表：
{terminology}

待翻译内容：
{content}

请直接输出翻译结果，无需解释。
```

**批量翻译策略**：

对于结构化内容（如表格），将整表内容发送给LLM翻译，一次性完成。

**翻译输出格式**：LLM会直接输出翻译后的内容，保持原有格式（表格保持表格结构，段落保持段落结构）。

**注意事项**：
- 对于大批量内容，建议分批翻译避免token限制
- 关键数据（数字、批号、有效期）必须与原文完全一致
- 保持原文备份，便于核对

### 附录8：关键属性清单

**必须设置的属性**（缺少会导致格式错误）：

| 属性 | 元素 | 说明 |
|------|------|------|
| `xml:space="preserve"` | `<w:t>` | 保留文本中的空格，必须用于包含空格的文本 |
| `encoding="UTF-8"` | XML声明 `<?xml?>` | 所有XML文件必须在声明中指定UTF-8编码 |
| `xmlns:w` | 根元素 | WordprocessingML命名空间声明 |

**常用可选属性**（根据需求添加）：

| 属性 | 用途 | 示例值 |
|------|------|--------|
| `w:val="single"` | 单下划线 | `<w:u w:val="single"/>` |
| `w:val="double"` | 双下划线 | `<w:u w:val="double"/>` |
| `w:jc="center"` | 居中对齐 | left/center/right/both |
| `w:type="auto"` | 自动列宽 | 用于表格列宽自适应 |
| `w:type="dxa"` | 绝对单位（twips）| 用于表格列宽固定值 |

## 质量控制要点

### 1. 保真度检查
- 检查文字完整性和准确性
- 验证表格行列数是否与原图一致
- 对比元数据与实际XML内容
- *快速验证法：将docx解压，检查document.xml结构*

### 2. 格式一致性
- 字体家族正确嵌入
- 表格边框样式统一
- 页边距和纸张大小符合预期
- 对齐方式与图片一致

### 3. 兼容性测试
- 在Microsoft Word中打开测试
- 在WPS Office中验证
- 检查是否提示"兼容模式"
- 尝试编辑内容，验证是否可正常修改

## 常见问题与解决方案

### 问题1：Word打开报错"文件损坏"
**原因**：XML格式错误或ZIP结构问题
**解决**：
1. 解压docx文件，检查XML文件格式是否合法（标签闭合、编码声明）
2. 确保`[Content_Types].xml`包含所有Override声明
3. 检查关系文件中的路径是否正确（使用相对路径，正斜杠`/`）
4. 使用在线XML验证器检查document.xml

**快速修复**：将.docx改为.zip，解压后重新压缩（确保目录结构正确）

### 问题2：文档内容显示异常
**原因**：编码不一致或字体缺失
**解决**：
1. 所有XML文件使用UTF-8编码保存
2. 确保XML声明包含`encoding="UTF-8"`
3. 在styles.xml的`w:rFonts`中指定英文字体（w:ascii="Calibri"）
4. 如有残留中文内容，确保w:eastAsia="SimSun"已指定

### 问题3：表格边框不显示
**原因**：样式未正确应用或border属性缺失
**解决**：
1. 在styles.xml中定义TableGrid样式并包含`w:tblBorders`
2. 或在表格属性中直接定义边框（`<w:tblBorders>`）
3. 确保边框颜色不是白色（w:color="000000"表示黑色）
4. 检查边框粗细（w:sz="4"是正常粗细，数值越大越粗）

### 问题4：文档打开后空白
**原因**：缺少根元素或sectPr位置错误
**解决**：
1. 确保document.xml有完整的`<w:document>`和`<w:body>`结构
2. 确保`<w:sectPr>`是`<w:body>`的最后一个子元素（在表格/段落之后）
3. 检查XML是否被意外截断

## 扩展能力

### 模板化
- 建立常见文档类型的样式模板（日志表、报告、申请表）
- 提取可复用的styles.xml和fontTable.xml作为模板
- 创建配置驱动的转换流程（JSON配置+内容数据 → docx）
- *应用场景：同一格式不同数据的批量生成（如月度报告）*

### 图片嵌入
- 对于源文档中的logo、公章、签名等图片元素
- 在docx中嵌入图片需要在word/目录下创建media/文件夹
- 在document.xml.rels中添加图片关系
- 在document.xml中使用`<w:drawing>`元素引用图片
- *适用于需要保留原始图片元素的场景*

### 非文字内容处理

对于无法直接转为文字的视觉元素：

| 元素类型 | 标注方式 | 处理策略 |
|----------|----------|----------|
| 印章 | `[SEAL: XXX公司印章]` | 保留占位标注，提醒用户补充 |
| 签名 | `[SIGNATURE: 张三]` | 保留占位标注，提醒用户补充 |
| Logo | `[LOGO: XXX公司]` | 如有原图可嵌入，否则占位标注 |
| 流程图 | `[DIAGRAM: 描述内容]` | 用文字描述结构，提醒用户补充 |
| 化学式 | 保留原文 | 化学式不翻译，精确复制 |
| 条码/二维码 | `[BARCODE/QRCODE]` | 保留占位标注 |

**原则**：非文字内容不丢弃，必须保留占位信息，确保用户知道原文此处有该元素。

## 最佳实践

1. **增量开发**：先构建最小可运行的docx（1个段落），再逐步添加样式和表格
2. **版本控制**：保留中间文件（HTML、XML）便于调试和回滚，存放在`temp/`目录，任务完成后清理
3. **标准化命名**：使用规范的ID和关系命名（rId1, rId2...），避免冲突
4. **元数据完善**：填写core.xml中的标题、作者、主题信息，便于文档管理
5. **文档注释**：在关键XML节点添加XML注释`<!-- 说明 -->`，提高可维护性
6. **快速验证**：每完成一个阶段就验证，不要等全部完成再测试
   - 阶段2完成 → 浏览器打开HTML检查布局
   - 阶段4完成 → Word打开docx检查格式
7. **编码一致性**：所有文件使用相同编码（推荐UTF-8 without BOM）
8. **备份原始图**：始终保留原始图片作为参照，方便比对

## 工具依赖

- **ZIP打包**：Node.js用`archiver`，Python用`zipfile`标准库，或命令行`zip`
- **PDF拆图**：`pdftoppm`、`PyMuPDF`
- **XML生成**：由LLM直接生成，无需XML库

---

**总结**：本技能提供从概念到实现的完整方法论。关键成功因素：
1. 准确理解图片内容和结构
2. 关键数据精确复制（数字、批号、有效期等），专业术语翻译准确
3. 严格遵守OOXML规范（XML格式、命名空间、文件结构）
4. 正确处理ZIP打包（关系文件不压缩，其他文件DEFLATE压缩）
5. 多页文档使用独立子任务处理，子代理写文件返回摘要，避免主代理上下文膨胀

实际执行时，先通读全文理解整体流程，再参考附录中的模板和代码片段。遇到问题时先检查XML格式，再检查ZIP结构，最后检查内容逻辑。保持灵活性，根据具体场景调整实现细节。
