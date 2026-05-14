# Python-docx 学术报告生成模板（WSL环境）

> 适用于 Windows WSL 环境下生成中文 Word 文档（论文报告、数据分析报告等）
> 场景：minimax-docx 的 .NET SDK 在 WSL 中不可用时，使用 python-docx 代替

## 环境准备

```bash
# WSL 中系统 Python 被管控，创建虚拟环境
python3 -m venv /tmp/docenv
/tmp/docenv/bin/pip install python-docx Pillow -q
```

## 标准脚本结构

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成[文档标题] - 报告"""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

# ===== 路径配置 =====
RESULT_DIR = "/mnt/d/你的Windows路径/输出文件夹"
IMG_DIR = RESULT_DIR  # 图片同目录

def set_cell_bg(cell, color_hex):
    """设置表格单元格背景色（蓝色标题栏用）"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def add_image(doc, path, width=None):
    """添加图片到文档（自动检查文件存在）"""
    if os.path.exists(path):
        doc.add_picture(path, width=width or Inches(5.5))
        return True
    return False

# ===== 创建文档 =====
doc = Document()
style = doc.styles['Normal']
style.font.name = 'Times New Roman'
style.font.size = Pt(12)

# ===== 章节标题 =====
doc.add_heading('第一章  标题', level=1)

# ===== 表格示例 =====
table = doc.add_table(rows=3, cols=3)
table.style = 'Table Grid'
headers = ['列1', '列2', '列3']
for i, h in enumerate(headers):
    cell = table.rows[0].cells[i]
    cell.text = h
    set_cell_bg(cell, '4472C4')
    for run in cell.paragraphs[0].runs:
        run.font.color.rgb = RGBColor(255, 255, 255)
        run.bold = True
data = [['A', 'B', 'C'], ['D', 'E', 'F']]
for i, row_data in enumerate(data):
    for j, val in enumerate(row_data):
        table.rows[i+1].cells[j].text = val

# ===== 插入图片 =====
img_path = os.path.join(IMG_DIR, '图片名.png')
if add_image(doc, img_path, width=Inches(5.5)):
    doc.add_paragraph('图1 图片标题')
else:
    doc.add_paragraph('[图片：图片名.png 未找到]')

# ===== 保存（关键：用 /mnt/d/... 格式）=====
output_path = os.path.join(RESULT_DIR, '输出文档名.docx')
doc.save(output_path)
print(f"已生成：{output_path}")
print(f"大小：{os.path.getsize(output_path) / 1024:.1f} KB")
```

## 关键注意事项

1. **路径格式**：WSL中必须用 `/mnt/d/...`，不能用 `D:\\...`
2. **中文字体**：python-docx 默认字体不支持中文，需要在每个 `run` 中设置中文字体：
   ```python
   run.font.name = 'Times New Roman'
   run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
   ```
3. **表格行数**：创建时 `rows=N` 要包含表头，所以实际数据行 = N-1
4. **图片嵌入**：docx内嵌图片用zip存储，可通过 `zipfile` 检查是否成功：
   ```python
   import zipfile
   with zipfile.ZipFile('output.docx') as z:
       imgs = [f for f in z.namelist() if 'media' in f]
       print(f"嵌入图片数：{len(imgs)}")
   ```
5. **write_file 局限性**：`write_file` 工具只能写文本，不能写 .docx/.xlsx 等二进制文件，必须用 Python 脚本 + `terminal` 执行
6. **写完必须验证文件存在**：脚本输出 `SUCCESS` 或 exit_code=0 不代表文件真的写成功了（WSL路径权限问题会导致静默失败）。必须再执行一次 `ls -la /path/to/file.docx` 确认文件大小 > 0。这是本工具链最高频的失败模式。

## 调试技巧

- 表格行列错位：检查 `rows=N` 是否足够（数据行+1表头）
- 图片未嵌入：确认文件存在 + 路径正确 + 磁盘空间足够
- 中文乱码：每个 `run` 都要设置中文字体
- 保存失败（FileNotFoundError）：输出目录不存在，用 `os.makedirs(RESULT_DIR, exist_ok=True)` 先创建
- 脚本成功但文件不存在：`/mnt/d/...` 路径拼写错误，或 WSL 权限问题。用 `ls -la` 逐级确认。
