# 开始使用 域包 · SM8 开始使用域(SM8 权威清单: .scratch/v2.0-spec-map/scenes/SM8-开始使用.md)
# 隔离契约: 本域文件集 = scripts/开始使用/ + templates/开始使用/ + render_开始使用 + tests/test_开始使用.py
# 公共层(scripts/home_manager/*)只读调用;seed_key 迁移 = D1 拆批前置批(T9,已并入 db.py 幂等迁移)

from . import ops

__all__ = ["ops"]
