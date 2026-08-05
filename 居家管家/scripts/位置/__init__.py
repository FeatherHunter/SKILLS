# 位置/__init__.py - SM2 空间与位置域(T3)
#
# 隔离契约(实施编排 map):本域只动 scripts/位置/ + templates/位置/ +
# render_位置.py + tests/test_sm2.py + features/位置.md + scenes/SM2;
# 公共层(home_manager.py 接线 / render 映射表)只做最小注册。
#
# 数据基础:items / item_locations(现状 schema,location = 自由字符串路径);
# location_nodes + items.fixed_location = D1 批新结构,本域自带幂等
# ensure_schema(与 SM1 item_events 同模式),D1 批收编进 db.py init_db。
#
# 位置树组件归属:本域创建并冻结(2026-08-05 · map 并发约定「位置树=T3」);
# SM1 筛选浏览 2-4 等后续域复用/演进 = 公共层 ISSUE。

SKILL_VERSION = "居家管家 v2.0 (SM2 T3)"
