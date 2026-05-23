# 照片存储环境变量配置 - 修改总结

## 修改日期
2026年5月23日

## 修改概述

为居家管家技能添加了照片存储目录的环境变量配置功能，支持灵活配置照片存储路径。

## 修改的文件

### 1. `scripts/home_manager/db.py`

**修改内容**：
- 修复了 `SKILL_DIR` 路径计算（从 `parent.parent` 改为 `parent.parent.parent`）
- 添加了 `HOME_PHOTOS_DIR` 环境变量支持
- 优先使用环境变量，否则使用默认的 `photos/` 目录

**关键代码**：
```python
# 照片目录：优先使用环境变量，否则默认为技能目录下的 photos 文件夹
_photos_env = os.environ.get("HOME_PHOTOS_DIR")
PHOTOS_DIR = Path(_photos_env) if _photos_env else SKILL_DIR / "photos"
```

### 2. `scripts/home_manager/item_ops.py`

**修改内容**：
- 导入了 `PHOTOS_DIR` 配置
- 添加了 `get_photo_full_path()` 辅助函数
- 更新了 `_format_item()` 函数，显示照片完整路径
- 更新了 `item_detail()` 函数，同时显示相对路径和完整路径

**新增函数**：
```python
def get_photo_full_path(photo_relative_path):
    """根据相对路径获取照片的完整路径"""
    if not photo_relative_path:
        return None
    return PHOTOS_DIR / photo_relative_path
```

### 3. `references/database.md`

**修改内容**：
- 在文档开头添加了"环境变量配置"章节
- 说明了 `HOME_PHOTOS_DIR` 和 `SKILLS_DB_PATH` 两个环境变量
- 提供了使用示例和路径存储规则

### 4. `SKILL.md`

**修改内容**：
- 在"功能概述"中添加了照片管理功能说明
- 在"快速导航"表格中添加了照片存储配置的链接

## 新增的文件

### 1. `.env.example`

**用途**：环境变量配置示例文件

**内容**：
```bash
# 居家管家 - 环境变量配置示例
# 复制此文件为 .env 并修改为你的实际路径

# 照片存储目录（绝对路径）
HOME_PHOTOS_DIR=./photos

# 数据库文件所在目录（可选）
# SKILLS_DB_PATH=./.db
```

### 2. `scripts/test_photo_config.py`

**用途**：测试照片目录配置的脚本

**功能**：
- 显示当前环境变量配置
- 验证照片目录是否存在
- 显示目录中的照片数量
- 提供配置建议

**运行方式**：
```bash
cd 居家管家
python scripts/test_photo_config.py
```

### 3. `references/photo-storage.md`

**用途**：照片存储配置的详细文档

**内容**：
- 快速配置指南
- 环境变量设置方法（Windows/Linux/Mac）
- 照片命名规范
- 数据库存储说明
- 常见使用场景
- 故障排除指南
- 最佳实践建议

## 功能特性

### 1. 灵活的路径配置

- **默认配置**：使用技能目录下的 `photos/` 文件夹
- **自定义配置**：通过 `HOME_PHOTOS_DIR` 环境变量指定任意路径
- **支持多种场景**：本地存储、外部硬盘、云同步、NAS 共享等

### 2. 相对路径存储

- 数据库只存储相对路径（如 `14_优瞳隐形眼镜盒.jpg`）
- 完整路径 = 环境变量 + 相对路径
- 便于迁移和备份

### 3. 智能路径显示

- 物品列表显示 `[图]` 标记
- 物品详情同时显示相对路径和完整路径
- 方便用户定位照片文件

### 4. 向后兼容

- 未设置环境变量时自动使用默认配置
- 现有照片文件无需迁移
- 保持与原有功能的完全兼容

## 使用示例

### 示例 1：使用默认配置

```bash
# 不设置环境变量，照片自动存储在 居家管家/photos/ 目录
# 无需任何配置，开箱即用
```

### 示例 2：配置外部硬盘

```bash
# Windows
set HOME_PHOTOS_DIR=E:\Backup\Photos\居家管家

# Linux/Mac
export HOME_PHOTOS_DIR=/mnt/external/photos/home-manager
```

### 示例 3：配置云同步目录

```bash
# OneDrive
set HOME_PHOTOS_DIR=C:\Users\用户名\OneDrive\居家管家照片

# Dropbox
set HOME_PHOTOS_DIR=C:\Users\用户名\Dropbox\居家管家照片
```

## 测试验证

### 测试 1：默认配置

```bash
cd 居家管家
python scripts/test_photo_config.py
```

**预期输出**：
- 显示照片目录：`D:\2Study\StudyNotes\SKILLS\居家管家\photos`
- 显示照片数量：17
- 提示：当前使用默认配置

### 测试 2：自定义配置

```bash
cd 居家管家
HOME_PHOTOS_DIR="D:\MyPhotos" python scripts/test_photo_config.py
```

**预期输出**：
- 显示照片目录：`D:\MyPhotos`
- 提示：已配置自定义路径

## 注意事项

### 1. 路径格式

- **Windows**：使用反斜杠 `\` 或正斜杠 `/`
- **Linux/Mac**：使用正斜杠 `/`
- 建议使用正斜杠，兼容性更好

### 2. 目录权限

- 确保程序有权限读写照片目录
- 外部硬盘需保持连接状态
- 网络共享需配置正确的访问权限

### 3. 文件命名

- 建议使用 `{物品ID}_{物品名称}.jpg` 格式
- 避免使用特殊字符（如 `\ / : * ? " < > |`）
- 保持命名的一致性

### 4. 备份策略

- 照片目录应纳入备份计划
- 定期备份数据库和照片文件
- 测试备份的可恢复性

## 后续优化建议

### 1. 自动照片命名

在添加物品时自动生成照片路径，无需手动输入。

### 2. 照片验证

在保存照片路径时验证文件是否存在。

### 3. 批量导入

支持批量导入照片并自动关联到物品。

### 4. 照片压缩

自动压缩照片以节省存储空间。

### 5. 缩略图生成

为物品列表生成缩略图，提高加载速度。

## 相关文档

- `references/database.md` - 数据库结构说明
- `references/photo-storage.md` - 照片存储配置指南
- `scripts/home_manager/db.py` - 数据库连接和配置
- `scripts/home_manager/item_ops.py` - 物品操作和照片处理
- `scripts/test_photo_config.py` - 配置测试脚本

## 版本信息

- **修改版本**：v1.0
- **修改日期**：2026-05-23
- **修改人**：AI Assistant
- **兼容性**：向后兼容，无需迁移现有数据
