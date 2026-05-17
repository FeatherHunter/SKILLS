---
name: 目录树
description: 目录树技能 - 递归扫描给定目录，输出所有目录和文件的树状结构清单
tags: [目录, 文件导航]
version: 3.2
---

# 目录树 · 技能文档

生成的HTML风格必须符合：
亮色单色背景 + 新禅意科技美学。

**视觉规范（v3.2+）：**
- 背景：纯净米白 `#f6f5f1`（单色，无渐变）
- 墨烟：极淡墨灰横向云雾纹理（CSS `repeating-linear-gradient` 实现，不喧宾夺主）
- 磨砂玻璃：`backdrop-filter: blur(10~20px)` + 1px 内嵌光晕边框
- 中心几何体：单线条三角 + 同心圆（SVG thin-line）
- 远山剪影：底部淡墨山影 SVG，opacity 0.5
- 按钮微光：hover 时 `box-shadow: 0 0 10px rgba(100,140,180,0.1)`
- 留白即呼吸：两栏布局，大量负空间

**注：** 背景色为浅色，视觉方向与 v3.1 的深色背景不同，以本节规范为准。

## 触发词

- `目录树`
- `目录导航`

---

## 核心功能

### 1. 扫描给定目录

递归扫描指定根目录，返回完整的目录和文件树结构。

- 扫描所有层级（深度无限制）
- 记录：name / path / is_dir / size / children[]
- `.git` 目录只显示自身及其文件数量，不递归其内部内容

### 2. 输出文件名命名规则

输出路径：`docs/directory-tree/`

文件名 = 取根目录**最后两个有意义段**，用下划线连接：

```
/mnt/d/2Study/StudyNotes         → 2Study_StudyNotes.html
/mnt/d/Work/Projects             → Work_Projects.html
/mnt/d/2Study/StudyNotes/SKILLS  → StudyNotes_SKILLS.html
D:\Work\Projects                  → Work_Projects.html
```

规则：
- 路径分隔符（/、\）→ 替换为 `_`
- 盘符保留（如 `d_`、`D_`）
- 特殊字符清理
- 后缀为 `.html`

### 3. 多根目录管理

同一个根目录每次生成覆盖同名文件，不同根目录生成不同文件名，不会冲突。

---

## 输入确认流程

```
Step 1：读取环境变量 DIR_NAV_ROOT
        → 有值 → 验证路径存在 → 直接使用

Step 2：无环境变量 → 检查会话状态 current_root
            → 有 → 直接使用
            → 无 → 询问用户输入路径

Step 3：用户输入路径 → 验证存在 → 存入会话状态
```

---

## 强制 HTML 生成规则（所有生成任务必须遵守）

### 规则1：默认全部折叠

- **所有目录默认折叠**，包括根目录的第一层子目录
- 用户点击才能展开
- 不能有任何目录在页面加载时默认展开

### 规则2：每项必有复制按钮

- **每个目录和每个文件**右侧必须有「复制路径」按钮
- 点击后复制该目录或文件的**绝对路径**
- 路径格式,同时提供两个系统的：
  - WSL 路径（以 `/mnt/` 开头）→ 直接复制，如 `/mnt/d/2Study/StudyNotes/SKILLS`
  - Windows 路径（以 `D:\` 等盘符开头）→ 保持原格式复制，如 `D:\Work\Projects`

### 规则3：其他规范

- 纯静态 HTML，无需服务器，双击即可打开
- 无 emoji
- 路径格式自动判断 WSL / Windows

### 规则4：必须使用tast-skill 和 ui-ux-pro-max-skill 这两个技能

### 规则5：必须使用superpowers 技能 写代码

### 规则6：顶级视觉风格

neo-Zen 新禅意科技美学，单色米白背景——墨汁云烟极淡横向纹理在背景中缓慢弥散，银灰细线几何体（三角+同心圆）居于画面正中，纳米级细腻磨砂玻璃作为行级材质，古老书法笔触解构为极简导航线条与电路纹理的融合形态，远山剪影在底部淡入为朦胧的远红外热感成像，按钮点缀含蓄的冷调银蓝微光，留白即呼吸，侘寂残缺之美融入冷冽精密的科技理性，8K 高清，文化纵深与数字静谧交织

---

## 工作流程

```
用户：目录树
    ↓
确认根目录（环境变量 / 会话状态 / 用户输入）
    ↓
检测 docs/directory-tree/ 下是否已有对应文件
    ↓
有缓存 → 询问用户：「更新？还是打开已有文件？」
         → 输入「更新」→ 重新扫描生成
         → 输入其他 → 打开现有 HTML
无缓存 → 直接生成
    ↓
生成完毕 → 告知用户文件路径
```

---

## 生成脚本

生成脚本位于同目录 `scripts/generate.py`，可直接运行：

```bash
python scripts/generate.py "/mnt/d/2Study/StudyNotes"
```

脚本目录结构：
```
SKILLS/目录树/
├── SKILL.md              # 本文档
├── generate.py          # 主生成脚本（see scripts/）
├── scripts/
│   ├── generate.py      # 主脚本
│   └── .scan_record.json # 最近一次扫描记录（自动生成）
└── example/
    └── 2Study_StudyNotes.html  # 完整样例（当前 StudyNotes 目录树）
```

---

## 大数据目录优化技术（≥10 万条目）

普通目录树对大目录（10 万级以上条目）有三大瓶颈：

1. **Python `os.walk` / `scandir` 在 WSL DrvFs 上极慢**（超时）
2. **内存中构建完整 JSON 树 → 字符串拼接 → HTML 体积爆炸**（461MB）
3. **一次性渲染所有 DOM 节点 → 浏览器卡死**

### 解决思路：三层分离

```
Step 1: find 命令流式输出到文件（绕过 Python I/O 瓶颈）
         find [root] -not -path "*/.git/*" -printf "%y|%p|%s|%h\n" > /tmp/dir-tree-raw.txt

Step 2: Python 快速解析 raw 文件（不做路径操作，只字符串 split）
         每行: kind|path|size|parent
         取 name: rsplit("/", 1)

Step 3: 树结构数据 zlib 压缩后 base64 嵌入 HTML（不参与 DOM）
         顶层目录渲染为折叠状态 DOM
         展开时 JS 从压缩数据动态解压渲染子节点（lazy render）
```

### 文件格式设计

```
# find 输出格式（每行一条目）
d|/mnt/d/root/subdir|4096|/mnt/d/root
f|/mnt/d/root/subdir/file.txt|1234|/mnt/d/root/subdir

# 树结构压缩格式（dir 行，\x00 分隔父子）
/mnt/d/root/dir1\x00child1\x00child2\x00...
/mnt/d/root/dir1/subdir\x00...
```

### 压缩效果（实测 StudyNotes 目录）

| 目录规模 | raw 树数据 | zlib 压缩后 | HTML 最终体积 |
|---------|-----------|------------|--------------|
| ~13 万条目 | ~59MB | ~3MB | **3.9MB** |
| 旧方案（全 DOM 预渲染） | — | — | **461MB** |

### 实现代码骨架

**Step 1: find 输出到文件**
```python
import subprocess
with open("/tmp/dir-tree-raw.txt", "wb") as f:
    subprocess.Popen([
        "find", root,
        "-not", "-path", "*/.git/*",
        "-printf", "%y|%p|%s|%h\\n"
    ], stdout=f).wait()
```

**Step 2: 快速解析（不做路径操作，只做字符串 split）**
```python
nodes = {}
with open("/tmp/dir-tree-raw.txt", "rb") as f:
    for raw in f:
        parts = raw.decode().rstrip().split("|")
        kind, path, size = parts[0], parts[1], int(parts[2])
        si = path.rfind("/")
        name = path[si+1:]
        nodes[path] = {
            "name": name,
            "is_dir": kind.lower() == "d",
            "size": size,
            "children": []
        }

# 构建 children 引用
for path in list(nodes):
    pi = path.rfind("/")
    parent = path[:pi]
    if parent in nodes:
        nodes[parent]["children"].append(path)
```

**Step 3: 树数据压缩嵌入**
```python
import zlib, base64

dir_lines = [
    path + "\x00" + "\x00".join(n["children"])
    for path, n in nodes.items()
    if n["is_dir"] and n["children"]
]
all_lines = "\n".join(dir_lines)
compressed = zlib.compress(all_lines.encode("utf-8"), level=6)
compressed_b64 = base64.b64encode(compressed).decode("ascii")
# HTML 中: window.__treeData = compressed_b64
```

**Step 4: 浏览器 JS 解压（pako）**
```javascript
const bstr = atob(window.__treeData);
const buf = new Uint8Array(bstr.split("").map(c => c.charCodeAt(0)));
const text = new TextDecoder().decode(pako.inflate(buf));

const treeIndex = {};
text.split("\n").forEach(line => {
  const nullIdx = line.indexOf("\x00");
  if (nullIdx < 0) return;
  const parent = line.slice(0, nullIdx);
  const children = line.slice(nullIdx + 1).split("\x00").filter(Boolean);
  treeIndex[parent] = children;
});


// 展开时 lazy render 子节点
function toggle(path) {
  if (expanded.has(path)) { /* collapse */ }
  else {
    expanded.add(path);
    const nested = item.querySelector(".nl");
    if (!nested.innerHTML)
      nested.innerHTML = renderChildren(treeIndex[path] || []);
  }
}
```

### CDN 依赖

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/pako/2.1.0/pako.min.js"></script>
```

> `pako` 是唯一外部依赖（zlib decompress），纯前端无需服务器。

### 何时启用

当 `find [root] -not -path "*/.git/*" | wc -l` 超过 **5 万条目**时，
自动切换为压缩 lazy-render 模式。

---

## 输出结果

每个生成任务返回：
- 扫描到的总条目数（目录 + 文件）
- 扫描耗时
- HTML 文件路径
- GitHub Pages 访问地址（如果已 push）


---

## 错误处理

| 情况 | 处理 |
|------|------|
| 根目录路径无效 | 报错并重新询问 |
| 目录无法访问 | 提示「无权限访问该目录」|
| 空目录 | 正常返回空树结构 |
| 扫描中断 | 返回已扫描的部分 + 警告 |