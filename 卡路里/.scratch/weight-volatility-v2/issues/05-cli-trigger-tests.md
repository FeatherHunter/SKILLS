# 05 — CLI + `--text` + 触发词 + 10 测试套件

**What to build:**
最终集成层,把 v2 暴露为用户可调用的命令 + 触发词:
- `render_weight_volatility_v2.py` CLI 接 `--start --end --baseline rolling|goal --text --output` 参数
- `_triggers.py` 注册 `查体重波动 v2`(别名 `查体重稳定性`)触发词
- `tests/test_weight_volatility_v2.py` 10 个 seam 4 测试全绿
- `scripts/check_html_responsive.py` 36 模板全 PASS
- `scripts/check_trigger_consistency.py` 三边一致

这是完整交付层,前面 4 ticket 的功能通过这层暴露给用户。

**Blocked by:** 04(toggle + trend + mobile)

**Status:** ready-for-agent

- [ ] `scripts/render_weight_volatility_v2.py` 新建,接 `--start --end` (默认最近 30 天) + `--baseline rolling|goal` (默认 rolling) + `--text` (纯文本模式) + `--output <path>`
- [ ] 输出路径:`calorie_html/查体重波动_v2_<YYYYMMDD>_<HHMMSS>.html`(同秒冲突自动 _2/_3 后缀)
- [ ] stdout:`⚠️ ACTION=SEND_TO_USER | HTML=<绝对路径>`
- [ ] `scripts/_triggers.py` 注册 `查体重波动 v2` 与别名 `查体重稳定性`,CLI 指向 `render_weight_volatility_v2.py`
- [ ] `scripts/render_help_center.py` 重 render,`卡路里.html` 根镜像同步
- [ ] seam 4 test 2:subprocess 跑 render exit 0 + HTML 生成
- [ ] seam 4 test 7:跑 render 后 weight_log 记录数不变(纯只读)
- [ ] seam 4 test 8:`--text` exit 0 + stdout 非 HTML
- [ ] `python -m pytest tests/test_weight_volatility_v2.py` 10 个 case 全绿
- [ ] `python -m pytest tests/` 全套 118+ passed,0 regression
- [ ] `python scripts/check_html_responsive.py` 36 模板全 PASS
- [ ] `python scripts/check_trigger_consistency.py` 三边一致
- [ ] 端到端 demo:invoke `查体重波动 v2` 触发词 → render 出 HTML → 打开看 3 KPIs + Canvas + 异常列表
