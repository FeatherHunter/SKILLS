---
Status: ready-for-agent
Slug: weight-history-table-mobile-redesign
Created: 2026-07-30
Source: /triage + Playwright 实测 · user BUG report · 体重趋势 mobile 表格"丑"
Depends on: 2389d7a (前序 commit 修通表格 4 列,本 ticket polish 设计)
---

# Triage Notes · AGENT BRIEF · 体重历史 mobile 表格 polish(Playwright 实测更新版)

## What's broken

user 实测 mobile(iPhone SE 375x667)说"丑"。我跑 Playwright 拿实测数据修正 triage 列表。

## What's established so far (Playwright 实测,2026-07-30)

### 🔴 HIGH(必修)

- **H1 · SVG 过高过低 = 100px on mobile** (回退!)
  - 原因: 我 commit `2389d7a` 改了 `height:clamp(180,40vh,320)` → `height:auto`,SVG 按 viewBox 800x260 比例算 height: 309*260/800 = **100px** — **太矮**
  - 影响: 折线+文字几乎看不见
  - 修复: 改 `height: min(280px, 40vw)`(响应式但保底线 280)
  - 或者: `height: clamp(180px, 30vw, 320px)`(在 375px 宽下 = 112.5px 太矮,改用 min)

- **H2 · note 列 "晨起空腹" 文字被 padding 挤** (实测)
  - data: `noteWidth: 85, noteScrollWidth: 85, noteOverflow: true`
  - 原因: `padding: 6px 4px` × 2 = 8px 横向 padding,content 区只有 77px,4 字符 + padding > 77px
  - 修复: `padding: 6px 6px`(少 2px)OR `width: 30%`(增加 5%,总宽 92px)

### 🟡 MEDIUM(应做)

- **M1 · 缺 sticky header** (24 行表滚 1168px 高)
  - 修复: `thead th { position: sticky; top: 0; background: var(--card); z-index: 1; }`

- **M2 · delta 列应 chip 化**
  - 当前: 裸数字 + color,视觉弱
  - 修复: `td.delta` 加 `display: inline-block; padding: 2px 8px; border-radius: 10px; background: rgba(color, .1)`

- **M3 · KPI 4 卡 mobile 2x2 但数字贴边**
  - 修复: `font-size: 20px → 17px` 在 @media (max-width:640px) 块

### 🟢 LOW(polish)

- **L1 · line-height 1.6 太散**
  - 修复: 表格 `line-height: 1.4` 在 mobile

- **L2 · 趋势箭头**
  - 修复: delta 字符加 `font-weight: 700` + 1.2em

- **L3 · empty state**
  - 修复: items.length === 0 时显示"暂无数据"

## What's in scope

- 修改 `templates/weight_history.html` `<style>` 段 + mobile @media 块
- 5-7 个 CSS 规则改动
- 加 6-8 个新 TDD tests

## What's out of scope

- 不重写 table 为 grid(单独 ticket)
- 不改 render script
- 不改 weight_volatility_v2.html(已 Canvas 化)
- 不改 desktop CSS(只在 mobile @media 块增加)

## What we need from you (@implement agent)

### 修顺序(从 high 到 low)

1. **H1**: SVG `height: clamp(180px, 30vw, 280px)` — 保证 280px 上限,小屏不超矮
2. **H2**: note 列 `padding: 6px 4px` → `4px 6px`(垂直 4,水平 6 — 略减少水平 padding)
3. **M1**: 加 sticky thead
4. **M2**: delta chip 化
5. **M3**: KPI mobile 字号 17
6. **L1**: table line-height 1.4 (mobile)
7. **L2**: delta font-weight
8. **L3**: empty state (可选,简单加)

## Acceptance criteria

- [ ] `python -m pytest tests/ -k weight_history` 全过(8 + 新 6-8 个 polish tests)
- [ ] `python scripts/check_html_responsive.py` 36 模板全 PASS
- [ ] Playwright 实测 iPhone SE 375x667:
  - [ ] SVG 高度 ≥ 140px
  - [ ] "晨起空腹"文字完整可见无截断
  - [ ] 滚动表头 sticky 在顶部
  - [ ] 整体无 horizontal scroll
  - [ ] 截图证据保存
- [ ] 桌面 1280x800 视觉无 regression

## Blocked by

- `2389d7a` (前序 commit) — 已在 main

## Out of scope

- ADR / CONTEXT / _triggers 更新
- HTML 改 <table> 为 <div> grid
- 改 BMI/体重 sparkline
- 加搜索/排序/分页