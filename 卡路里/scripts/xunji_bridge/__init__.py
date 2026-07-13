#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""训记 ↔ 卡路里 适配桥。

包内模块(分层):
    原子层(训记 API 1:1,无业务):
        auth       KEY 管理(XUNJI_TRAINS_KEY 优先,fallback XUNJI_API_KEY)
        catalog    训记官方动作名校验
        fetch      训记 POST /api_trains_for_llm_v2(读)
        upsert     训记 POST /api_upsert_trains_for_llm_v2(增/改,client_request_id 唯一性兜底)

    应用层(组合底层 + 业务逻辑):
        push       推 plan:plan→res[] 转换 + 45s 限频 + 调 upsert(同进程,localid=0 新建)
        overlay    覆盖 plan:fetch 拿 localid + plan→res[] + 调 upsert(同进程,start/end=0)
        backfill   fetch + xunji_adapter → exercise_log(幂等)
        run_sync   后台串行 N 天同步(写状态文件供 cron 唤醒)
"""
from . import auth, catalog, fetch, upsert, push, overlay, backfill, errors, run_sync  # noqa: F401

__version__ = "1.2.0"
__all__ = ["auth", "catalog", "fetch", "upsert", "push", "overlay", "backfill", "errors", "run_sync", "__version__"]
