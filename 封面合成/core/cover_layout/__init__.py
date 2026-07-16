"""
封面合成 scripts/layout.py
③ 业务层:布局引擎

支持 layout 类型:
- symmetric-cascade(默认,适合主图 + 左右副图,镜像对称)
- cascade(主图 + 左右副图,堆叠)
- polaroid(主图 + 多副图,极地风)
- grid(网格平铺)

每个 layout 输出 list[LayerSpec],由 compose.py 消费
"""
from dataclasses import dataclass
from typing import List, Tuple
from math import sqrt


@dataclass
class LayerSpec:
    """单个图层的规格"""
    path: str
    target_w: int          # 缩放后宽度
    target_h: int          # 缩放后高度
    x: int                 # paste x(canvas 坐标)
    y: int                 # paste y(canvas 坐标)
    angle: float = 0       # 旋转角度(度)
    z: int = 0             # z-order,数字越大越在上层
    opacity: float = 1.0   # 暂时不用,留给将来

    @property
    def bbox(self):
        """旋转后 bbox 的画布坐标 (x1, y1, x2, y2),考虑旋转"""
        diag = int(sqrt(self.target_w ** 2 + self.target_h ** 2)) + 20
        # 旋转后 bbox 居中于 (x + w/2, y + h/2)
        cx, cy = self.x + self.target_w // 2, self.y + self.target_h // 2
        return (cx - diag // 2, cy - diag // 2, cx + diag // 2, cy + diag // 2)


def calc_asymmetric_cascade(canvas_w: int, canvas_h: int,
                            photo_paths: List[str]) -> List[LayerSpec]:
    """asymmetric-cascade layout(主图 + 左右副图,堆叠)

    主图(第 1 张):中央,大尺寸
    左图(第 2 张):左侧,中等尺寸
    右图(第 3 张):右侧,中等尺寸
    其他图(第 4+ 张):叠在主图上,小尺寸

    防坑:
    - #11 重复缩小主图,主图消失 → 主图固定大小,左右缩小入侵
    """
    layers = []

    # 主图(照片 1):画布 70% 大小,中央
    main_size = min(canvas_w, canvas_h) * 0.65
    main_w = main_size
    main_h = main_size * (canvas_h / canvas_w)  # 按画布比例
    main_x = (canvas_w - main_w) // 2
    main_y = (canvas_h - main_h) // 2
    layers.append(LayerSpec(
        path=photo_paths[0],
        target_w=int(main_w),
        target_h=int(main_h),
        x=int(main_x),
        y=int(main_y),
        angle=0,
        z=1,  # 主图在最下
    ))

    # 左图(照片 2):画布 50% 大小,左边
    if len(photo_paths) >= 2:
        left_size = min(canvas_w, canvas_h) * 0.5
        left_w = left_size
        left_h = left_size * (canvas_h / canvas_w)
        left_x = canvas_w * 0.04  # 距画布左 4%
        left_y = (canvas_h - left_h) // 2
        layers.append(LayerSpec(
            path=photo_paths[1],
            target_w=int(left_w),
            target_h=int(left_h),
            x=int(left_x),
            y=int(left_y),
            angle=-14,
            z=2,  # 左图在主图之上
        ))

    # 右图(照片 3):对称左图,距右 4%
    if len(photo_paths) >= 3:
        right_size = min(canvas_w, canvas_h) * 0.5
        right_w = right_size
        right_h = right_size * (canvas_h / canvas_w)
        right_x = canvas_w - right_w - int(canvas_w * 0.04)
        right_y = (canvas_h - right_h) // 2
        layers.append(LayerSpec(
            path=photo_paths[2],
            target_w=int(right_w),
            target_h=int(right_h),
            x=int(right_x),
            y=int(right_y),
            angle=-14,  # 对称左图 -14° → 14° → -14°(视觉上对称,虽然 -14 顺时针 -14 逆时针)
            z=2,
        ))

    # 第 4+ 张:叠在主图上,小尺寸,降 z-order
    for i, p in enumerate(photo_paths[3:], start=4):
        size = min(canvas_w, canvas_h) * 0.25
        layers.append(LayerSpec(
            path=p,
            target_w=int(size),
            target_h=int(size * (canvas_h / canvas_w)),
            x=canvas_w // 2 - int(size // 2),
            y=canvas_h // 2 - int(size // 2),
            angle=(i * 7) % 30 - 15,  # -15 ~ +15 度的随机旋转
            z=3 + i,
        ))

    return layers


def calc_cascade(canvas_w: int, canvas_h: int,
                 photo_paths: List[str]) -> List[LayerSpec]:
    """cascade layout(主图 + 堆叠副图,右倾叠放)"""
    layers = []
    # 主图
    main_size = min(canvas_w, canvas_h) * 0.65
    main_w = main_size
    main_h = main_size * (canvas_h / canvas_w)
    layers.append(LayerSpec(
        path=photo_paths[0],
        target_w=int(main_w), target_h=int(main_h),
        x=(canvas_w - int(main_w)) // 2,
        y=(canvas_h - int(main_h)) // 2,
        angle=0, z=0,
    ))

    # 副图依次向右下偏移
    offset = 40
    for i, p in enumerate(photo_paths[1:], start=1):
        size = min(canvas_w, canvas_h) * 0.35
        sw, sh = int(size), int(size * (canvas_h / canvas_w))
        layers.append(LayerSpec(
            path=p,
            target_w=sw, target_h=sh,
            x=canvas_w - sw - 60 + i * offset,
            y=canvas_h - sh - 60 - i * offset,
            angle=-5 + i * 4,
            z=i + 1,
        ))
    return layers


def calc_polaroid(canvas_w: int, canvas_h: int,
                  photo_paths: List[str]) -> List[LayerSpec]:
    """polaroid layout(拍立得风,主图中央,副图在四角散落)"""
    layers = []
    # 主图中央
    main_size = min(canvas_w, canvas_h) * 0.55
    layers.append(LayerSpec(
        path=photo_paths[0],
        target_w=int(main_size),
        target_h=int(main_size * (canvas_h / canvas_w)),
        x=(canvas_w - int(main_size)) // 2,
        y=(canvas_h - int(main_size * (canvas_h / canvas_w))) // 2,
        angle=-2, z=1,
    ))

    # 副图散落四角
    side_size = min(canvas_w, canvas_h) * 0.3
    sw, sh = int(side_size), int(side_size * (canvas_h / canvas_w))
    angles = [-15, 12, -8, 18]
    positions = [
        (60, 60),  # 左上
        (canvas_w - sw - 60, 60),  # 右上
        (60, canvas_h - sh - 60),  # 左下
        (canvas_w - sw - 60, canvas_h - sh - 60),  # 右下
    ]
    for i, p in enumerate(photo_paths[1:5], start=0):
        if i >= len(positions): break
        layers.append(LayerSpec(
            path=p,
            target_w=sw, target_h=sh,
            x=positions[i][0], y=positions[i][1],
            angle=angles[i], z=i + 2,
        ))
    return layers


def calc_grid(canvas_w: int, canvas_h: int,
              photo_paths: List[str]) -> List[LayerSpec]:
    """grid layout(网格平铺,适合多图无主图场景)"""
    import math
    n = len(photo_paths)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    cell_w = canvas_w // cols
    cell_h = canvas_h // rows
    layers = []
    for i, p in enumerate(photo_paths):
        r = i // cols
        c = i % cols
        layers.append(LayerSpec(
            path=p,
            target_w=cell_w - 20,
            target_h=cell_h - 20,
            x=c * cell_w + 10,
            y=r * cell_h + 10,
            angle=0, z=0,
        ))
    return layers


LAYOUTS = {
    "symmetric-cascade": calc_asymmetric_cascade,
    "cascade": calc_cascade,
    "polaroid": calc_polaroid,
    "grid": calc_grid,
}


def get_layout(name: str):
    """获取 layout 函数,未知名字 fallback 到 asymmetric_cascade"""
    return LAYOUTS.get(name, calc_asymmetric_cascade)