# 联动.py 域包 · SM9 联动功能域(SM9 权威清单: .scratch/v2.0-spec-map/scenes/SM9-联动功能.md)
# 隔离契约: 本域文件集 = scripts/联动/ + templates/联动/ + render_联动.py + tests/test_联动.py
# 公共层(scripts/home_manager/*)只读调用,不修改;公共层变更走 ISSUE+review(T2 奠基除外)
# 场景资产: references/scenarios.yaml 的 SM9 段(合并器未接入前直接改该段)

from . import ops

__all__ = ["ops"]
