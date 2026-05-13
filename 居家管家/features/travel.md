# 旅游归位

## 出门前

### Step 1

用户说"居家管家 我要带XX出去旅游"

### Step 2

AI 搜索并确认要带哪些物品

### Step 3

用户确认 → 执行：

```bash
python home_manager.py update --id 5 --location-status "旅游中"
```

---

## 回家后

### Step 1

用户说"居家管家 旅游回来了"

### Step 2

查询所有"旅游中"物品：

```bash
python home_manager.py search --status "旅游中"
```

### Step 3

逐个询问："这东西放回原位还是换位置？"

### Step 4

用户逐一确认 → 更新状态为"在家"，并更新位置

```bash
# 放回原位
python home_manager.py update --id 5 --location-status "在家"

# 换位置
python home_manager.py update --id 5 --new-location "新位置" --location-status "在家"
```