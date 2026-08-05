# 物品.py 域包 · SM1 物品管理域(SM1 权威清单: .scratch/v2.0-spec-map/scenes/SM1-物品管理.md)
# 隔离契约: 本域文件集 = scripts/物品/ + templates/物品/ + render_物品 + scenes/SM1.yaml + tests/test_物品.py
# 公共层(scripts/home_manager/*)只读调用,不修改;公共层变更走 ISSUE+review(T2 奠基除外)

from . import events
from . import validators
from . import ops

__all__ = ["events", "validators", "ops"]
