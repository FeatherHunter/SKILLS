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
| "看看有哪些食品" | `--category-id 137` (顶级·食物与饮品) |
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
- `--category-id` 分类 ID(顶级/二级自动展开下级,整数)
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

## Step 4: 默认输出 HTML

`查物品 / 看物品 / 统物品` 一律默认输出 HTML 页面；不保留 `-html` 后缀唤醒词。

### CLI 行为

```bash
# 查物品 → 走 templates/search_results.html
python home_manager.py search --name "牛奶" --limit 20

# 看物品 → 走 templates/item_detail.html
python home_manager.py detail --id 631

# 统物品 → 走 templates/list_overview.html
python home_manager.py list --limit 100
```

输出默认路径在技能目录 `output/`，可通过 `--output` 显式指定。

### 数据契约

页面通过 `<script id="payload" type="application/json">` 注入数据；渲染器统一 `{status, data, message}` 三段式。

### 模板与渲染器

- 模板目录：`templates/`
- 渲染器：`scripts/home_manager/html_render.py`
- 输出目录：`output/`

### 发文件给用户

将生成的 HTML 路径通过渠道发给用户；模板只展示数据，不直连数据库。

> 注意：不新增 `-html` 后缀唤醒词；如需 JSON 数据，用 `*_items_json` 等辅助函数。