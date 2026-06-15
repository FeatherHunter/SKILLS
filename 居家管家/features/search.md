# 查物品 / 看物品

## 流程概述

1. 解析搜索条件
2. 执行搜索
3. 处理搜索结果

---

## Step 1: 解析搜索条件

AI 从用户输入提取：
- 名称关键词
- 位置片段
- 标签
- 分类
- 状态

### 示例

| 用户说 | 解析结果 |
|--------|----------|
| "找卧室里白色的T恤" | `--name "T恤" --tag "白色" --location "卧室"` |
| "黑色的杯子" | `--name "杯子" --tag "黑色"` |
| "冰箱里的牛奶" | `--name "牛奶" --location "冰箱"` |
| "看看有哪些食品" | `--category "食品"` |
| "找在家的东西" | `--status "在家"` |

---

## Step 2: 执行搜索

```bash
python home_manager.py search --name "T恤" --tag "白色"
```

支持组合搜索：
- `--name` 物品名称（支持模糊匹配）
- `--location` 位置（支持模糊匹配）
- `--tag` 标签（精确匹配）
- `--category` 分类
- `--status` 位置状态
- `--exact` 名称精确匹配（不加则模糊匹配）
- `--limit` 返回数量上限（默认20）

---

## Step 3: 处理搜索结果

### 0 条结果

告知用户未找到匹配物品，询问是否换个关键词或新建物品。

### 1 条结果

直接展示物品信息。

### 多条结果

列出让用户选择（注意：不默认选任何一个），选中后用 detail 查看详情：

```bash
python home_manager.py detail --id {选中ID}
```

---

## Step 4: 生成 HTML 页面（仅当唤醒词含 "-html"）

### 触发条件

用户输入包含查物品/看物品/盘全部-html 等**查询类唤醒词**，且以 `-html` 结尾。

> 匹配规则：最长匹配。`查物品-html` 优先于 `查物品`。

### 数据获取

1. 从 Step 3 解析出物品 ID 列表和搜索条件
2. 根据条件类型执行对应的 `--json` 命令：
   - `查物品-html`：`python home_manager.py search --name "XX" --json`（或其他搜索参数组合）
   - `看物品-html`：`python home_manager.py detail --id {ID} --json`
   - `盘全部-html`：`python home_manager.py list --json`
3. `--json` 命令返回 JSON 格式结构化数据（完整字段，含 photo 相对路径）

### 照片处理

1. 解析 JSON 中每个物品的 `photo` 字段（相对路径）
2. 用环境变量 `HOME_PHOTOS_DIR` 拼接完整路径：`PHOTOS_DIR / photo`
3. 读取图片文件，二进制 → Base64 编码
4. 嵌入 HTML：`<img src="data:image/jpeg;base64,{base64字符串}">`
5. 读取失败时：显示占位符（灰色图标 + "图片未找到"）

### HTML 生成规则

1. **风格**：苹果风 / 简约 / 视觉舒适（由 AI 现场发挥，不写死 CSS）
2. **结构**：所有物品以卡片形式垂直排列在同一 HTML 页面中
3. **字段**：包含该物品在数据库所有表（items / item_tags / item_locations）的**所有字段**
4. **位置分布**：每个物品的每个位置单独展示（含数量、状态、购买/过期日期）
5. **标签**：完整展示 item_tags 表中的所有标签
6. **自含**：单文件 HTML，无外部依赖

### 输出

1. 将 HTML 存入临时文件：`/tmp/home_query_{timestamp}.html`
2. 告知用户文件路径

### 发文件给用户

**QQ 渠道**（channel=qqbot）：通过 QQBot 发文件方式发送路径

**微信渠道**（channel=weixin）：通过微信渠道发文件方式发送路径

> 注意：此步骤不改变任何脚本，只在 Skill 层定义行为规范。