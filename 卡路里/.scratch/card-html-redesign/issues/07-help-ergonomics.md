Status: ready-for-agent

# 07 — HELP HTML ergonomics

**What to build:** `卡路里_HELP_<TS>.html` 三项 UX 升级:
1. `.word-card > summary` 行加 `.copy-btn.copy-main`(右贴,1-click 复制 main prompt)
2. 每个 TRIGGER 加 `fill_hints: [...]` 字段,`_prompt_skeleton()` 在 tail 后追加填空提示
3. hero 字号上调(h1 220% / stats 115% / sub 105%),首 category 与 hero 视觉连续(margin-top 0)

依据:D2(spec 实现细节)。

**Blocked by:** None — can start immediately

- [ ] `_triggers.py` 每个 TRIGGER 加 `fill_hints: []`(默认空);`_prompt_skeleton(wake, body, variant=None, fill_hints=[])` 拼接逻辑更新
- [ ] 帮助台输入型 TRIGGER(查热量 / 记吃了 / 记体重 / 记运动 / 记喝水 / 存食品 / 改食品 / 设营养目标 / 设体重目标 / 记体脂 / 记围度 / 记身材照 / 开卡路里[指定日期]) 填上对应 fill_hints
- [ ] `templates/help_center.html` `.word-card > summary` 加 `.copy-btn.copy-main`(右贴 `margin-left: auto`),点击复制 `main_prompt.text`
- [ ] hero CSS 调整:`h1: 150% → 220%`;`stats: 100% → 115%`;`sub: 100% → 105%`;`.cat-block:first-of-type { margin-top: 2px → 0 }`;hero 与首 cat 背景过渡微连续
- [ ] mobile `@media (max-width: 640px)` 同步调整 hero 与 copy 按钮 padding
- [ ] 测试:展开 L1 后,所有 L2 列表上均有可见 copy 按钮;hero 字号按设计值;`check_prompt_quality.py` 校验 fill_hints 拼接到 prompt 末尾