---
name: Github导航台
description: Github导航台技能 - 扫描 STUDYNOTES_DOCS 目录，生成 structure.json 动态数据，部署到 GitHub Pages
tags: [文档导航, GitHub Pages, HTML]
version: 3.0
---

# Github导航台 · 技能文档

生成HTML页面必须要是该风格：
历史图书馆数字档案网站，温暖的学术怀旧——泛黄羊皮纸与岁月斑点纹理，dark academia 深勃艮第红、墨黑、黄铜金的色调，维多利亚时代植物铜版画用作雅致的装饰分隔线，Garamond 风格衬线字体与宽裕的行距，一摞古董皮面书在页脚处隐约淡出，钨丝台灯光线投下柔和的暗角阴影，图书馆目录卡的检索美学，博物馆级数字策展，光束中飞舞的微尘，沉静的智性氛围

## 触发词

- `更新文档导航`
- `导航台`
- `docs 导航`

---

## AI 工作流（Agent 执行步骤）

当用户触发上述任意关键词时，AI 必须依次执行以下步骤：

### 步骤 1：检查并配置环境变量

> **OpenClaw 必须优先执行此步骤，未配置完整不得进入步骤 2。**

在继续之前，AI 必须确认两个环境变量已配置：

- `STUDYNOTES_DOCS` — 导航台根目录的绝对路径
- `GITHUB_PAGES_BASE` — GitHub Pages 根地址，结尾必须带 `/`

**判断逻辑：**

1. AI 先尝试在**自身运行环境**中读取这两个环境变量
2. 如有任一缺失 → 询问用户缺失变量的值，并将两个变量都写入 `SKILLS/Github导航台/.env` 文件（供 Python 脚本使用）
3. 两者都缺失 → 依次询问，先问 `STUDYNOTES_DOCS`，再问 `GITHUB_PAGES_BASE`
4. 询问时给出明确格式要求（路径 vs URL），不要让用户猜测

**注意：** OpenClaw 的进程环境与系统环境变量独立，不要假设系统变量已对 AI 进程可见。未配置完整时必须引导用户配置，不能跳过。

### 步骤 2：运行 generate_nav.py

在 `SKILLS/Github导航台/` 目录下执行：

```bash
cd "$SKILL_DIR"
python generate_nav.py
```

此脚本会扫描 `STUDYNOTES_DOCS` 环境变量指定的目录，在 **SKILL 目录下**生成 `structure.json`。

### 步骤 3：运行 deploy.py

在同一个目录下执行：

```bash
python deploy.py
```

此脚本完成：扫描 → 复制 index.html → git commit + push。

### 步骤 4：报告结果

告知用户：
- 生成了哪些子目录和文件
- 是否已推送到远程仓库
- GitHub Pages 大约 1-2 分钟后自动更新

---

### 快速判断：是否需要重新部署

运行前先检查 `STUDYNOTES_DOCS` 目录自上次部署后有无变化：

```bash
cd "$STUDYNOTES_DOCS"
git status --porcelain
```

如有变化才执行步骤 2-3；如无变化，告知用户"已是最新"。

---

## 设计思路

### 核心架构

```
SKILL 目录/
├── generate_nav.py    # 扫描 $STUDYNOTES_DOCS 目录
├── deploy.py          # 一键部署脚本
├── index.html         # 导航台页面
├── structure.json     # 由 generate_nav.py 生成（部署时复制到目标目录）
├── .env               # 路径配置（自动生成）
└── SKILL.md           # 本文档

STUDYNOTES_DOCS 目录（GitHub Pages 部署目录）/
├── index.html         # 导航台首页（由 deploy.py 从 SKILL 目录复制）
├── structure.json     # 动态数据（由 deploy.py 从 SKILL 目录复制）
└── ...                # 其他子目录和 HTML 文件
```

### 数据流

```
deploy.py 运行
    ↓
generate_nav.py 扫描 $STUDYNOTES_DOCS 目录结构
    ↓
在 SKILL 目录下生成 structure.json（子目录 + 根文件列表）
    ↓
deploy.py 复制 index.html + structure.json → $STUDYNOTES_DOCS/
    ↓
git commit + push → GitHub Pages 自动更新
    ↓
用户访问 GitHub Pages → index.html fetch structure.json → 动态渲染
```

### 为什么这样设计

1. **静态部署 + 动态内容**：GitHub Pages 只能托管静态文件，通过 JSON 数据文件实现内容动态化
2. **环境变量隔离**：导航台路径通过环境变量配置，脚本可跨环境复用
3. **一键部署**：deploy.py 将扫描、复制、推送三步合一
4. **无需手动维护**：每次部署自动扫描目录结构，永远与实际文件同步

---

## 首次使用：环境变量配置

### 第一步：设置环境变量

在系统环境变量中添加两个变量：

```
变量名: STUDYNOTES_DOCS
值: <你的导航台根目录绝对路径>

变量名: GITHUB_PAGES_BASE
值: <你的 GitHub Pages 根地址，结尾必须带 />
  例如: https://<用户名>.github.io/<仓库名>/
```

**Windows 方法**：设置 → 系统 → 关于 → 高级系统设置 → 环境变量 → 新建用户变量

### 或者：让脚本引导配置

如果不设置环境变量，首次运行 `generate_nav.py` 时会依次提示你输入两个路径，输入后自动保存到 `.env` 文件。

---

## 使用方法

### 方式一：一键部署（推荐）

```bash
cd "$SKILL_DIR"
python deploy.py
```

自动完成：扫描 → 生成 JSON → 复制文件 → git 推送

### 方式二：分步执行

```bash
# 1. 扫描 STUDYNOTES_DOCS 目录生成 structure.json
python generate_nav.py

# 2. 将 index.html 和 structure.json 复制到 $STUDYNOTES_DOCS/
# （需要先设置环境变量 STUDYNOTES_DOCS）
```

### 方式三：在 Claude Code 中触发

直接对 AI 说「更新文档导航」，AI 会引导你运行部署流程。

---

## 文件说明

### generate_nav.py

扫描 `STUDYNOTES_DOCS` 环境变量指定的目录，在 **SKILL 目录下**生成 `structure.json`。

**输入**：`STUDYNOTES_DOCS` 目录结构
**输出**：`SKILL目录/structure.json`

JSON 格式：
```json
{
  "subdirs": [
    {
      "name": "directory-tree",
      "path": "directory-tree/",
      "files": [{ "name": "2Study_StudyNotes.html", "label": "目录树" }]
    }
  ],
  "rootFiles": [
    { "name": "index.html", "label": "本导航台", "isEntry": true }
  ]
}
```

### deploy.py

三步流程：
1. 运行 `generate_nav.py` 生成 `structure.json`
2. 复制 `index.html` 和 `structure.json` 到 `STUDYNOTES_DOCS` 目录
3. 检查 git 变化，有变化则 commit + push

### index.html

导航台页面，**UI 样式完全不变**，数据来源从硬编码改为 `fetch('structure.json')` 动态加载。

---

## 环境变量说明

| 变量名 | 必须 | 说明 |
|--------|------|------|
| `STUDYNOTES_DOCS` | 是 | 导航台根目录的绝对路径 |
| `GITHUB_PAGES_BASE` | 是 | GitHub Pages 根地址，结尾带 `/`，如 `https://<用户名>.github.io/<仓库名>/` |

**配置优先级**：
1. 系统环境变量（永久）
2. `.env` 文件（同目录，首次运行自动生成）
3. 脚本内兜底值（向上三级到 SKILL 所在项目根目录，仅作为最后兜底）

> 两个环境变量都需要设置，缺一不可。

---

## 错误处理

| 情况 | 处理 |
|------|------|
| 环境变量未设置 | 提示用户输入，输入后保存到 `.env` |
| 目标路径无效 | 报错退出，提示检查 `STUDYNOTES_DOCS` 环境变量 |
| structure.json 加载失败 | 控制台报错，显示空状态 |
| git push 失败 | 报错，本地文件保留 |

---

## 部署到 GitHub Pages

1. 确保 `STUDYNOTES_DOCS` 目录是 GitHub 仓库的 GitHub Pages source
2. 运行 `deploy.py`
3. 等待 1-2 分钟，GitHub Pages 自动更新

---

## 目录规范

- 所有文件放在 `SKILLS/Github导航台/` 目录下
- `SKILL目录/structure.json` 由 `generate_nav.py` 自动生成，**不要手动编辑**
- `$STUDYNOTES_DOCS/index.html` 和 `$STUDYNOTES_DOCS/structure.json` 由 `deploy.py` 复制覆盖，不要在导航台目录里直接修改
