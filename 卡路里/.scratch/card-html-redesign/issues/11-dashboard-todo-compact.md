Status: ready-for-agent

# 11 — 主页 dashboard 今日待办 compact

**What to build:** `主页仪表盘` "今日待办" 区 4 行内容在一屏内可见;新增右侧 state icon(完成/未完成 视觉化)。

依据:D3(spec 实现细节)。

**Blocked by:** None — can start immediately

- [ ] `.todo-row` padding 14 → 11;label 15 → 14;meta 12 → 11.5;check 22 → 20
- [ ] 新 `.state` 元素:done → 绿色 dot / pending → 空心圆;priority badge 仍叠加(如有)
- [ ] meta 文案保持(`已记录 N 条`),不动(由后续 Q4 决策时再优化)
- [ ] mobile `@media (max-width: 640px)`:state icon 与 priority badge 共占右侧不溢出
- [ ] 测试:mock todos 4 条 + 完成度 4 / 2 / 0 三档 fixture 都渲染;手机 360px 视口无溢出