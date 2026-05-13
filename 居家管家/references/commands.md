# 命令行参考

## 初始化

```bash
python home_manager.py init
```

## 添加物品

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

## 搜索物品

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
python home_manager.py list --sort dormant   # 按长期未访问排序
python home_manager.py list --sort name      # 按名称排序（默认）
```

---

## 物品详情

```bash
python home_manager.py detail --id 1
```

---

## 物品盘点

```bash
python home_manager.py inventory --location "卧室/衣柜"
```

---

## 频率统计

```bash
# 高频物品
python home_manager.py stats --type frequent --limit 20

# 长期未访问
python home_manager.py stats --type dormant --limit 20

# 总体统计
python home_manager.py stats --type summary
```

---

## 标签管理

```bash
# 列出所有标签
python home_manager.py tag-list

# 合并标签
python home_manager.py tag-merge --from "白" --to "白色"
```

---

## 账号管理

```bash
# 初始化 master key（首次使用）
python home_manager.py account init --master-key "你的密钥"

# 添加账号
python home_manager.py account add --platform "淘宝" --user "xxx" --pass "xxx" --master-key "你的密钥"

# 列出账号
python home_manager.py account list

# 查看密码（需要 master key）
python home_manager.py account show --platform "淘宝" --master-key "你的密钥"

# 删除账号
python home_manager.py account del --platform "淘宝"

# 修改 master key
python home_manager.py account set-master --master-key "旧密钥" --new-master-key "新密钥"
```