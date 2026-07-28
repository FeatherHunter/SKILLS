# 02 — 完整 template→command_cn 映射表 + 12.B HELP 命名

**Status:** resolved
**Resolved:** 2026-07-28

## Answer

Implemented in `scripts/render/__init__.py`:
- `TEMPLATE_TO_COMMAND_CN` dict at module level, all 9 non-help_center templates registered with their 中文 command_cn
- `_auto_output_path()` checks `if template_name == "help_center.html"` → 12.B branch produces `居家管家_HELP_<stamp>.html`; else → 12.A branch looks up `TEMPLATE_TO_COMMAND_CN`
- New templates only need to add a line to the mapping dict

Tests added in `tests/test_render.py` (13 new, all green):
- test_12a_naming_for_all_templates (parametrized 9 templates × expected command_cn)
- test_12b_help_naming_uses_skill_cn_name_and_HELP_keyword
- test_help_keyword_is_greppable
- test_travel_trip_uses_chuxing_qingdan_superset_name
- test_delivery_check_distinguished_from_search_results

End-to-end verified:
- `python home_manager.py search` → `home_manager_html/查物品_*.html`
- `python home_manager.py help` → `home_manager_html/居家管家_HELP_*.html`

## What to build

(Original ticket body preserved below)

**What to build:** 把 T1 硬编码的"查物品"改为查 `TEMPLATE_TO_COMMAND_CN` 静态映射 dict,10 个 template 全部登记。非 help_center 的 9 个走 12.A 路径(`<command_cn>_<datetime>.html`),help_center 走 12.B 路径(`居家管家_HELP_<datetime>.html`)。新增 template 时只需在映射表加一行。

**Blocked by:** 01 — env 链解析 + 12.A 自动命名(单 template tracer)

- [x] `TEMPLATE_TO_COMMAND_CN` dict 在 render 层定义,登记全部 10 个 template:
  - `search_results` → 查物品
  - `delivery_check` → 查快递
  - `add_preview` → 录物品
  - `item_detail` → 看物品
  - `list_overview` → 统物品
  - `inventory_check` → 盘物品
  - `expiring_alert` → 查过期
  - `outfit_picker` → 穿什么
  - `travel_trip` → 出行清单
  - `help_center` → (特殊,走 12.B 路径,不进映射表的 command_cn 字段,而是单独识别)
- [x] 9 个非 help_center template 参数化测试,每个生成的文件名前缀正确
- [x] `render_page("help_center.html", ok_payload)` 不传 output_path → 文件落在 `<env_root>/home_manager_html/居家管家_HELP_<YYYYMMDD>_<HHMMSS>.html`(12.B 命名,`_HELP_` 保留字)
- [x] `_HELP_` 保留字在文件名中段,可被 grep 一抓出来
- [x] `travel_trip` 用综合名 `出行清单`(涵盖带物品 pack + 归物品 return,不拆 template)
- [x] `delivery_check` 映射到 `查快递`,与 `search_results` 的 `查物品` 区分开(CLI 在 `--status 快递中` 时自动切 template,文件名跟着变)
- [x] 现有 test_help_center.py 集成测试(走 CLI `python home_manager.py help --output`)继续通过
- [x] 全部 69 个原有 pytest 测试继续通过
