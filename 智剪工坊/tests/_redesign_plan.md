# 重写 intent.html — v0.7 设计

## 核心变化

### 删除
- 删除「视频序列」顶层独立区域（`<section id="sequences-section">`）
- 删除 `addSequence` / `addSequenceRow` / `refreshAllSequenceDropdowns` / `rebuildSequenceTransitions` 等序列相关函数
- 删除 `collectFormData` 里的 sequences 收集逻辑
- 删除旧 chains/forced_order 兼容性代码

### 新增：视频卡片折叠
每个 video-card 默认折叠（只显示缩略图+文件名），点击展开显示全部字段。
- `.video-card` 加 `.collapsed` class 控制折叠
- 缩略图区域可点击切换折叠状态
- 第一个卡片默认展开

### 新增：每个视频的「下一个视频」+ 「转场特效」
在 video-card 底部加一个新字段区（折叠区内）：
- **下一个视频**：下拉选其他视频（不能选自己，不能选已被其他视频指向的视频，不能形成循环）
- **转场特效**：选了「下一个视频」后出现（fade/淡入淡出 / cut/直切 / dissolve/溶解 / wipe-left/左擦除 / wipe-right/右擦除 / slide-up/上滑 / zoom-in/推进 / blur/模糊）
- 字段加在 `<div class="op-row">` 之后

### 约束逻辑（JS）
1. 不能选自己（`videoEntries[i]` 排除 `i`）
2. 不能一对多：被其他视频指向过的视频不在下拉中
   → 维护 `incomingRefs = Set<entry.index>`
3. 不能循环：选了下一个视频后，递归检查目标视频的「下一个」链，若链中已含自己则拒绝
4. 每个视频只能有一个「下一个视频」（天然满足）

### 保存逻辑
`collectFormData` 重建 sequences：
- 遍历 `videoEntries`，找「没有任何视频指向自己」的起点（多个 = 多个 sequence）
- 从每个起点顺着「下一个视频」链走到终点，重建 `sequences[i].videos = [文件名数组]`
- 转场从每个视频的字段读取，存为 `transitions`

### intent.json 格式（不变）
`sequences[i].videos` 仍然是文件名数组，和现在兼容。

### 兼容
- 加载 `existingIntent.sequences` 时：**忽略**（因为新格式不用它了）
- 加载旧 chains/forced_order 时：**忽略**
