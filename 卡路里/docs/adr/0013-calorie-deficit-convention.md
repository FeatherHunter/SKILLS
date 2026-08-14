# 热量缺口统一约定：符号（正=缺口）+ 基准口径（TDEE 默认 / BMR 独立命名）

Status: accepted

Issue #332 冒烟发现 `render_calorie_deficit` 渲染失败（3 处 SQL 列名错误），wayfinder 盘点（#349/#351）暴露更深问题：「热量缺口」在代码里 8 处实现、符号两派（series 系「负=缺口」≈12 消费点 vs 自算渲染器「正=缺口」7 处）、基准四散（TDEE / BMR / TDEE−300 / 固定 1700），且新分析层自身不自洽——隔离临时库实测：真实缺口用户（摄入 2000 < 消耗 2607）在「模拟减重」场景被预测为**增重**（weekly_loss = −0.28 kg/周）。

我们决定：

1. **符号统一为「正=缺口」**：热量缺口 = 消耗 − 摄入，正值为缺口（减重潜力），负值为盈余。series.py `deficit` 字段公式翻转（`exp − calories`），docstring 同步修正（原 L22「负数=盈余」与公式自相矛盾）。
2. **基准双口径并存、明确命名**：
   - **热量缺口（TDEE 口径，默认）** = TDEE + 运动消耗 − 摄入。series 系（组合分析/健康报告/趋势/诊断/预测）统一用此口径。
   - **基础代谢缺口（BMR 口径，独立命名）** = BMR + 运动消耗 − 摄入。`diet_deficit_analysis` / 健康仪表盘 / 主页缺口公式条专用；术语表（CONTEXT.md）区分命名，禁止混用。
3. **残留基准归一**：`render_calorie_deficit.py` 的「TDEE−300」（300=TEF 假设）去掉 −300 归入 TDEE 口径；`render_exercise_distribution.py` / `render_lint_health.py` 的硬编码 1700 改为读档案 TDEE。
4. **字段名保留 `deficit`**，只改方向与 docstring（改名无收益、徒增改动面）。
5. **术语落点**：`卡路里/CONTEXT.md`（本 ADR 配套，Q4 拍板）。

考虑过的选项：
- **统一为「负=缺口」**（保留 series 公式、翻转 7 个自算渲染器）——自算渲染器数量少但用户直觉与 legacy/diet 两处均为「正=缺口」，且「负=缺口」与 docstring 矛盾延续混乱，否决。
- **单基准（只留 TDEE，BMR 全部替换）**——`diet_deficit_analysis` 被 dashboard/主页/健康报告独立管线消费，且 BMR 口径本身有独立语义（纯基础代谢），强行替换破坏既有消费方，否决；改为双口径命名区分。
- **TDEE−300 保留为统一基准**——TEF 是估算假设，与 series 系完整 TDEE 口径不可比，否决；TEF 留作可选参数而非默认。

后果：
- T3（符号统一修复 #352）实施面 = 翻转 series.py 公式 + 修正 anomaly.py 4 处判定、render_analysis.py（L288/L361/L522）、cross.py buckets、predict_report.html L154、calorie_deficit_eta 文案等，并同步 2 个自相矛盾夹具（mock_calorie_deficit.json / mock_exercise_*.json）；补回归测试（当前测试零锁定）。
- T4（查热量缺口场景归宿 #353）以「热量缺口 = TDEE 口径」为数据源选型基准。
- 主页缺口公式条（正=缺口）与 series 统一后口径一致，无需再翻转。

详见：`卡路里/CONTEXT.md` + wayfinder map #349（T1 决议 #350 / T2 盘点 #351）。
