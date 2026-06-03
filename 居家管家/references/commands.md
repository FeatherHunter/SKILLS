# 命令行参考

## 初始化

```bash
python home_manager.py init
```

## 录物品

```bash
# 基本用法
python home_manager.py add --name "物品名称" --category "分类" --location "位置路径" --tags "标签1,标签2"

# 完整参数
python home_manager.py add \
  --name "牛奶" \
  --category "饮品" \
  --location "客厅/冰箱/上层" \
  --quantity 3 \
  --owner "使用者" \
  --price 5.00 \
  --purchase-date "2025-05-01" \
  --expiration-date "2025-06-01" \
  --remark "备注内容" \
  --tags "牛奶,蒙牛" \
  --photo "photos/1.jpg" \
  --location-status "在家"
```

### 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| --name | 是 | - | 物品名称 |
| --category | 是 | - | 分类（参考 categories.md） |
| --location | 是 | - | 存放位置（必须至少两级路径，如 `客厅/冰箱`） |
| --quantity | 否 | 1 | 数量 |
| --owner | 否 | "使用者" | 所有者 |
| --price | 否 | - | 单价（元/件） |
| --purchase-date | 否 | - | 购买日期（YYYY-MM-DD） |
| --expiration-date | 否 | - | 过期日期（YYYY-MM-DD） |
| --remark | 否 | "" | 备注 |
| --tags | 否 | "" | 标签（逗号分隔） |
| --photo | 否 | "" | 图片路径 |
| --location-status | 否 | "在家" | 位置状态（在家/备用/借用中等） |

---

## 推荐位置（录物品辅助）

```bash
# 基础版：只显示位置+同类数量
python home_manager.py suggest-locations --category "衣物"

# 增强版：附带显示每个位置的代表物品名（推荐使用）
python home_manager.py suggest-locations --category "衣物" --with-examples

# 自定义返回数量
python home_manager.py suggest-locations --category "饮品" --with-examples --limit 5
```

### 参数说明

| 参数 | 说明 |
|------|------|
| --category | 必填，物品分类（如 衣物/饮品/电子） |
| --with-examples | 开关，加了之后每个位置附带 2 个代表物品名 |
| --limit | 返回位置数量上限，默认 10 |

### 输出示例

```
📍 位置推荐（衣物）：共 3 个位置
----------------------------------------------------------------------
  1. 卧室/衣柜/上层  [2件同类]
     └ 代表：黑色连帽卫衣、白色长袖T恤
  2. 卧室/抽屉       [1件同类]
     └ 代表：深蓝牛仔裤
  3. 客厅/衣帽架     [1件同类]
     └ 代表：灰色运动外套
  4. 其他位置（用户输入新位置）
```

---

## 参考定位（"和XX放一起"用）

```bash
# 根据参考物品名找它的所有位置
python home_manager.py find-location --reference "黑卫衣"

# 自定义候选数
python home_manager.py find-location --reference "黑卫衣" --limit 3
```

### 参数说明

| 参数 | 说明 |
|------|------|
| --reference | 必填，参考物品名（支持模糊匹配） |
| --limit | 候选物品数量上限，默认 5 |

### 输出示例

```
🔍 参考「黑卫衣」找到 2 件候选：
----------------------------------------------------------------------
  1. 黑色连帽卫衣  [ID:42]  分类:衣物
     └ 📍 卧室/衣柜/上层 ×1[在家]
  2. 黑色针织卫衣  [ID:67]  分类:衣物
     └ 📍 客厅/衣帽架 ×1[在家]
```

### 使用场景

录新物品时，用户说："放在和那件黑卫衣一样的位置" → AI 调用本命令 → 拿到 ID:42 + 位置 → 直接复用。

---

## 查物品

```bash
# 基本搜索
python home_manager.py search --name "牛奶"

# 组合搜索
python home_manager.py search --name "牛奶" --location "冰箱" --tag "蒙牛"

# 按状态搜索
python home_manager.py search --status "在家"

# 精确匹配
python home_manager.py search --name "牛奶" --exact
```

### 参数说明

| 参数 | 说明 |
|------|------|
| --name | 物品名称（支持模糊匹配） |
| --category | 分类 |
| --location | 位置（支持模糊匹配） |
| --tag | 标签（精确匹配） |
| --status | 位置状态 |
| --exact | 名称精确匹配（不加则模糊匹配） |
| --limit | 返回数量上限（默认20） |

---

## 更新物品

```bash
# 更新基本信息
python home_manager.py update --id 1 --name "新名称" --remark "新备注"

# 更新位置状态
python home_manager.py update --id 1 --location-status "备用"
python home_manager.py update --id 1 --location-status "借用中" --location "客厅/冰箱"

# 数量变化
python home_manager.py update --id 1 --minus 1      # 减少数量
python home_manager.py update --id 1 --plus 3       # 增加数量

# 移动位置
python home_manager.py update --id 1 --new-location "厨房/冰箱" --location "客厅/冰箱"

# 更新位置日期
python home_manager.py update --id 1 --purchase-date "2025-05-10" --location "客厅/冰箱"
python home_manager.py update --id 1 --expiration-date "2025-06-01" --location "客厅/冰箱"

# 追加新位置（一物多位置，心愿 ID: 84）
python home_manager.py update --id 1 --add-location "办公室/抽屉"
python home_manager.py update --id 1 --add-location "客厅/桌上" --add-quantity 2 --add-location-status "在家"
python home_manager.py update --id 1 --add-location "零食柜" --add-purchase-date "2026-06-01" --add-expiration-date "2027-06-01"
```

### 参数说明

| 参数 | 说明 |
|------|------|
| --id | 物品ID（必填） |
| --name | 物品名称 |
| --category | 分类 |
| --owner | 所有者 |
| --price | 单价 |
| --remark | 备注 |
| --tags | 标签（覆盖） |
| --photo | 图片路径 |
| --location | 指定要操作的位置（配合 --location-status/--purchase-date 等使用） |
| --location-status | 位置状态 |
| --new-location | 新存放位置（移动物品） |
| --quantity | 直接设置数量 |
| --minus | 减少数量 |
| --plus | 增加数量 |
| --purchase-date | 购买日期（YYYY-MM-DD，更新到位置级别） |
| --expiration-date | 过期日期（YYYY-MM-DD，更新到位置级别） |
| --add-location | 追加新位置（不替换现有位置，一物多位置） |
| --add-quantity | 追加位置的数量（默认1） |
| --add-reason | 追加位置的原因/备注 |
| --add-location-status | 追加位置的状态（默认在家） |
| --add-purchase-date | 追加位置的购买日期 |
| --add-expiration-date | 追加位置的过期日期 |

---

## 列表查询

```bash
# 列出所有物品
python home_manager.py list

# 按位置筛选
python home_manager.py list --location "卧室"

# 按状态筛选
python home_manager.py list --status "在家"

# 按分类筛选
python home_manager.py list --category "饮品"

# 排序
python home_manager.py list --sort recent    # 按最后访问排序
python home_manager.py list --sort frequent  # 按访问次数排序
python home_manager.py list --sort dormant   # 按查低频排序
python home_manager.py list --sort name      # 按名称排序（默认）
```

---

## 看物品

```bash
python home_manager.py detail --id 1
```

---

## 盘物品

```bash
python home_manager.py inventory --location "卧室/衣柜"
```

---

## 频率统计

```bash
# 查高频
python home_manager.py stats --type frequent --limit 20

# 查低频
python home_manager.py stats --type dormant --limit 20

# 查过期（心愿 ID: 1）
python home_manager.py stats --type expiring --days 30
python home_manager.py stats --type expiring --expired-only
python home_manager.py stats --type expiring --category "食品" --days 7

# 总体统计
python home_manager.py stats --type summary
```

### expiring 参数说明

| 参数 | 说明 |
|------|------|
| --days | 预警天数窗口（含已过期），默认 30 |
| --expired-only | 开关，只显示已过期物品 |
| --category | 按分类筛选（如 食品/医药用品/化妆品） |

---

## 看标签 / 合标签

```bash
# 看标签
python home_manager.py tag-list

# 合标签
python home_manager.py tag-merge --from "白" --to "白色"
```

---

## 查账号 / 存账号 / 改账号

```bash
# 初始化 master key（首次使用）
python home_manager.py account init --master-key "你的密钥"

# 存账号
python home_manager.py account add --platform "淘宝" --user "xxx" --pass "xxx" --master-key "你的密钥"

# 查账号（列出全部）
python home_manager.py account list

# 查账号（查看指定平台密码）
python home_manager.py account show --platform "淘宝" --master-key "你的密钥"

# 删除账号
python home_manager.py account del --platform "淘宝"

# 修改 master key
python home_manager.py account set-master --master-key "旧密钥" --new-master-key "新密钥"
```