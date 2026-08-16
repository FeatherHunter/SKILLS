# -*- coding: utf-8 -*-
"""iso_db · pytest 插件形式参考实现(已弃用 · 2026-08-14)

⚠️ 重要：pytest 9.x 在 conftest.py 通过 `pytest_plugins = ["iso_db"]` 加载
外部 plugin 时,hook 注册不可靠(实测 iso_db plugin 模块被加载但 hook 未注册)。

解决方案(#400 实施经验): 直接在卡路里/tests/conftest.py 内联 iso_db hooks
(`pytest_configure` + `iso_db_isolate` autouse fixture)。这是目前最稳健方案。

本文件保留作为参考实现和文档,未来如需重新启用 plugin 形式
(配合 entry_points),可参考此实现。

实际生效位置: 卡路里/tests/conftest.py L17-145 (内联版)
"""
# 此模块在当前 pytest 版本下不会被自动加载,仅作为参考
