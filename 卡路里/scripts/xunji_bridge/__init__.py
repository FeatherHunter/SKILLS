#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""训记 ↔ 卡路里 适配桥。

包内模块:
    auth       KEY 管理(XUNJI_TRAINS_KEY 优先,fallback XUNJI_API_KEY)
    catalog    训记官方动作名校验(读 ~/.minimax/训记官方动作.json)
    fetch      训记 GET /api_trains_for_llm_v2
    push       训记 POST /api_upsert_trains_for_llm_v2
    backfill   fetch + xunji_adapter → exercise_log(幂等)
"""
from . import auth, catalog, fetch, push, backfill, errors, run_sync  # noqa: F401

__version__ = "1.0.0"
__all__ = ["auth", "catalog", "fetch", "push", "backfill", "errors", "run_sync", "__version__"]
