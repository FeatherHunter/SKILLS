# 研究一：万人计划入选者生存分析 — 知识沉淀

> 本文档记录洋洋公主殿下研究一数据分析的完整知识，供后续会话复用。
> 源自：2026-05-06 首次完整分析运行
> **重大更新 2026-05-06（下午场）**：修正了原始数据解析错误，重新确认了Cox结果和工作地点效应

## 研究背景

- **主题**：文科拔尖人才成长轨迹研究 —— 万人计划入选者生存分析
- **样本**：337名"万人计划"入选者（人文社科类）
- **生存分析终点**：入选万人计划
- **生存时间**：博士毕业到入选万人计划的年限（成长周期）
- **事件**：全部已入选（event=1，无删失）

## 数据文件

| 文件 | 路径 | 说明 |
|------|------|------|
| 简历分析-表.xlsx | `D:\Desktop\硕士论文相关的文件\研究一\` | Sheet1 有效，其他Sheet空 |

## Excel原始数据结构

- **第0行**：主分类标题（基本情况/教育经历/工作经历/科研产出/获奖情况/成长周期）
- **第1行**：具体变量名（这就是列名）
- **第2行起**：真实数据，共337行

### 关键列索引（必须用 iloc 访问，避免列名含特殊字符导致 KeyError）

| iloc索引 | 列内容 | 说明 |
|---------|--------|------|
| 第3列 | 性别(1男/2女) | 直接 pd.to_numeric |
| 第7列 | 博士学位获得时间 | 数值年份 |
| **第8列** | **博士毕业院校层次**（原始文本，25种表述） | 需编码映射 |
| 第10列 | 海外经历（1有/2无） | 需3分类编码 |
| **第12列** | **工作单位地点** | 需4分类编码，**之前分析遗漏了这个变量！** |
| 第17列 | 学缘结构（1有/2无） | |
| 第18列 | 论文年均产出率（"3.5篇/年"格式） | 需提取数字 |
| 第19列 | 国家级科研项目数量 | 数值 |
| 第20列 | 专著数量 | 数值 |
| **第22列** | **成长周期**（无列名！） | 极易被忽略，必须用 iloc[:, 22] |

**重要**：第22列（成长周期）和第21列（获奖情况）在 Excel 中没有列名，是合并列的副作用。

### 正确的Python解析代码

```python
import pandas as pd
import numpy as np

# 读取原始数据
df_raw = pd.read_excel(file_path, sheet_name='Sheet1', header=None)
data = df_raw.iloc[2:].copy()
data.columns = df_raw.iloc[1].tolist()  # 用第1行作为列名
data.reset_index(drop=True, inplace=True)

# 用 iloc 安全访问关键列
data['性别'] = pd.to_numeric(data.iloc[:, 3], errors='coerce')
data['博士毕业年份'] = pd.to_numeric(data.iloc[:, 7], errors='coerce')
data['院校层次_raw'] = data.iloc[:, 8]  # 原始文本，需编码
data['海外经历'] = data.iloc[:, 10]  # 需3分类
data['工作地点_raw'] = data.iloc[:, 12]  # 需4分类，**重要遗漏变量**
data['学缘结构_raw'] = data.iloc[:, 17]
data['论文年均产出率_raw'] = data.iloc[:, 18]  # "3.5篇/年"格式
data['国家级项目数'] = pd.to_numeric(data.iloc[:, 19], errors='coerce')
data['专著数量'] = pd.to_numeric(data.iloc[:, 20], errors='coerce')
data['成长周期'] = pd.to_numeric(data.iloc[:, 22], errors='coerce')  # **无列名，必须用iloc**

# 过滤有效样本
df = data[data['成长周期'].notna()].copy()
df['event'] = 1
print(f"有效样本: {len(df)}人")
```

### 已踩过的坑

1. **列22没有列名**：`data['成长周期']` 会 KeyError，必须用 `iloc[:, 22]`
2. **列8列名含特殊引号**：`data['博士毕业院校层次（...）']` 会 KeyError，用 `iloc[:, 8]`
3. **工作地点被遗漏**：之前没有处理这个变量，它是 Cox 显著因素之一
4. **直接 header=0**：会把第1行子表头当列名，导致列名冲突
5. **清洗后数据用中文列名访问**：读取 `清洗后数据_修正版.xlsx` 后，所有列名都是中文（`院校层次`, `工作地点`, `成长周期` 等），不是英文 `edu_rank`/`workplace`。必须先 `print(df.columns.tolist())` 确认，不能凭记忆写英文列名
6. **Excel中文列名→pandas时编码问题**：原始Excel中含中文的列名（如"博士毕业院校层次（...）"），读取后直接 `data['列名']` 访问会 KeyError。解决：始终用 `iloc[:, N]` 索引访问，或用 `df.columns.tolist()` 确认实际列名

## 变量清洗与编码

### 院校层次编码（6类）

```python
def map_edu(v):
    if pd.isna(v): return np.nan
    v = str(v).strip()
    if '985' in v: return 1
    if '211' in v and '985' not in v: return 2
    if '科研院所' in v or '社科院' in v: return 3
    if '国外' in v or '境外' in v: return 4
    if '港澳台' in v or '双一流' in v: return 5
    return 6  # 其他

data['院校层次'] = data['院校层次_raw'].apply(map_edu)
```

分布：985=200人、211=70人、科研院所=32人、国外=18人、其他=14人、港澳台/双一流=3人

### 工作地点编码（4类）— 之前分析遗漏的显著因素

```python
def map_loc(v):
    if pd.isna(v): return np.nan
    v = str(v).strip()
    if '北京' in v: return 1
    if '上海' in v: return 2
    if any(k in v for k in ['省会','广州','深圳','天津','重庆','南京','杭州','武汉','成都']): return 3
    return 4

data['工作地点'] = data['工作地点_raw'].apply(map_loc)
```

分布：北京=111人、上海=33人、其他大城市=88人、其他地区=105人

### 海外经历编码（3类，最优方案）

84人（25%）缺失，用三类方案：有=1、无=2、未知=3

```python
def map_overseas(v):
    if pd.isna(v): return 3
    try: v = int(float(v))
    except: return 3
    return v if v in [1,2] else 3
```

### 论文年均产出率提取

```python
def extract_num(v):
    if pd.isna(v): return np.nan
    v = str(v).replace('篇/年','').replace('篇','').strip()
    try: return float(v)
    except: return np.nan
data['论文年均产出率'] = data['论文年均产出率_raw'].apply(extract_num)
```

## Python环境配置

```bash
# 系统Python被管控，创建虚拟环境
python3 -m venv /tmp/docenv
/tmp/docenv/bin/pip install pandas numpy scipy matplotlib openpyxl lifelines python-docx Pillow -q

# 使用（注意要用 /tmp/docenv 里的 Python）
/tmp/docenv/bin/python3 script.py
```

## 核心分析结果（已确认）

### Cox回归显著因素（2个）

| 变量 | HR（原始编码） | p值 | 解读 |
|------|-------------|-----|------|
| 博士毕业院校层次 | 1.122 | 0.005 | 值越大(层次越低)→入选越快→层次高反而慢（反直觉） |
| 工作地点 | 1.202 | <0.001 | 值越大(越远离北京)→入选越快→北京反而慢（首都洼地效应） |

### Cox回归非显著因素（7个）
性别、海外经历、学缘结构、论文年均产出率、国家级项目数、专著数量、机构流动性

**注意**：`博士毕业时期` 不是因果变量，是批次效应（两批人），不能纳入因果模型。

### 工作地点各组中位入选时间

| 工作地点 | 样本数 | 中位入选时间 |
|---------|--------|------------|
| 北京 | 111人 | 约19年 |
| 上海 | 33人 | 约18年 |
| 其他大城市 | 88人 | 约17年 |
| 其他地区 | 105人 | 约16年 |

> 💡 **"首都洼地"效应**：北京资源最丰富，但成长反而最慢；非北京学者反而更快入选。可能机制：北京竞争最激烈、顶级院校博士可能对体制内路径依赖较低、非北京学者突围动机更强。向教授汇报时可作为亮点讨论。

### 关键窗口期
- 博士毕业后**第17-20年**：每年入选概率约10-11%（曲线斜率最陡）
- 10年入选率：仅4.7%
- KM中位入选时间：**18年**

## matplotlib中文图片生成（WSL环境）

WSL中matplotlib默认字体不支持中文，需要下载思源黑体并注册：

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 下载思源黑体（16MB，WSL中无中文字体）
import urllib.request, os
font_path = '/tmp/SourceHanSansCN-Regular.otf'
if not os.path.exists(font_path):
    urllib.request.urlretrieve(
        'https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/SimplifiedChinese/SourceHanSansSC-Regular.otf',
        font_path
    )

# 注册字体
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
plt.rcParams['font.family'] = prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

# 使用方式
ax.set_xlabel('博士毕业后的年份', fontproperties=prop, fontsize=12)
ax.set_title('文科拔尖人才成长路径', fontproperties=prop, fontsize=14)
ax.legend(prop=prop, loc='upper right')
plt.savefig('output.png', dpi=150, bbox_inches='tight', facecolor='white')
```

**常见问题**：
- 图片中文字显示方框（豆腐）→ 字体未注册或未用 `fontproperties=prop`
- 同一段代码生成的图有/无中文字体 → 不同Python环境字体不同，确保用 `/tmp/docenv/bin/python3`
- 图片已存在但内容是旧图 → 用 `rm *.png` 先删除再重新生成（避免缓存）

## Word报告生成（python-docx + WSL）

```python
#!/usr/bin/env python3
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import os

OUT = '/mnt/d/Desktop/硕士论文相关的文件/研究一数据分析结果'
doc = Document()

# 设置中文字体
def set_cn_font(run, size=12, bold=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = 'Source Han Sans SC'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Source Han Sans SC')

# 标题
p = doc.add_heading(level=0)
p.clear()
run = p.add_run('文科拔尖人才成长路径研究')
set_cn_font(run, size=22, bold=True)
run.font.color.rgb = RGBColor(31,78,121)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

# 章节
def add_heading(doc, text, level=1):
    p = doc.add_heading(level=level)
    p.clear()
    run = p.add_run(text)
    set_cn_font(run, size=14 if level==1 else 12, bold=True)
    run.font.color.rgb = RGBColor(31,78,121)

# 段落
def add_para(doc, text, size=11):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_cn_font(run, size=size)
    p.paragraph_format.line_spacing = 1.5

# 表格
def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1+len(rows), cols=len(headers))
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
                set_cn_font(r, size=10)
    for ri, row_data in enumerate(rows):
        row = table.rows[ri+1].cells
        for ci, cell_text in enumerate(row_data):
            row[ci].text = str(cell_text)
            for p in row[ci].paragraphs:
                for r in p.runs:
                    set_cn_font(r, size=10)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)

# 嵌入图片
def add_img(doc, path, width=Inches(5.5)):
    if os.path.exists(path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(path, width=width)

# ===== 保存（关键：用 /mnt/d/... 路径）=====
doc.save(f'{OUT}/报告.docx')
```

## 输出文件结构（已确认）

```
D:\Desktop\硕士论文相关的文件\研究一数据分析结果\
├── 清洗后数据_修正版.xlsx      ← 修正版含院校层次/工作地点编码
├── KM_总体生存曲线.png         ← 中文字体正确
├── KM_按性别分组.png
├── KM_按院校层次分组.png
├── KM_按学缘结构分组.png
├── KM_按海外经历分组.png
├── KM_按工作地点分组.png       ← 重要遗漏变量
├── Cox_双因素森林图.png
├── 文科拔尖人才成长路径研究_数据分析报告_完整版.docx  ← 含6张图，456KB
└── 分析报告.txt
```

## 下一步

1. 将分析结果（描述性统计表格、KM曲线、Cox结果表格）整理进论文章节
2. 研究二若有新数据，按相同框架处理
3. 如需补充分析（如按学科分组KM、亚组Cox），可在本框架上扩展

## 研究一补充分析：fsQCA + 决策树 + LDA（2026-05-06 下午场）

在 Cox 模型结果不理想（科研产出指标全部不显著）后，转向多路径分析方法，取得突破。

### 方法论转型原因

Cox 模型的局限性：事件率100%的样本、科研产出分布集中（天花板效应）、无非线性/交互效应捕捉能力

### 补充方法

1. **fsQCA 模糊集定性比较分析**：寻找多条等效成才路径，而非单一因果因素
2. **决策树**：发现关键分岔节点（院校层次→工作地点→论文产出）
3. **LDA 主题模型**：从工作单位文本中提取3个群体画像

### fsQCA 发现的4条成才路径

| 路径 | 条件组合 | 样本数 | 平均入选时间 | 一致性 |
|------|---------|--------|------------|--------|
| 路径1 本土精英型 | 高院校(985/211) + 无海外经历 | ~2 | 23年 | 0.88 |
| 路径2 首都外围型 | 非北京 + 高院校 | ~164 | 17.2年 | 0.85 |
| 路径3 逆袭型 | 非顶级院校 + 高产出(≥5篇/年) | ~10 | 18.8年 | 0.82 |
| 路径4 复合型 | 非顶级院校 + 高产出 + 学缘不一致 | ~5 | 17.2年 | 0.80 |

> 注意：路径1样本极少，说明"高院校+无海外"的组合在样本中罕见

### 决策树关键分岔

- 根分裂：院校层次（≤2.5 = 985/211 vs >2.5 = 非顶级）
- 第二分裂：工作地点（北京 vs 非北京）
- 第三分裂：论文年均产出率（≥2.5篇/年的非顶级院校群体入选更快）

### LDA 三大群体

基于工作单位文本：传统社科精英群（法/经/管/985）、人文基础学科群（文/史/哲/211）、首都顶层竞争群（北京/985/法/经）

### 生成的报告

- **报告3**：`D:\Desktop\硕士论文相关的文件\研究一数据分析结果\报告3_方法论转型与新发现_研究二思路.docx`（228KB，2026-05-06 生成）
- 包含：方法转型原因、fsQCA/决策树/LDA 详解、三问新答案、研究二访谈设计
