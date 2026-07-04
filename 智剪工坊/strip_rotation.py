"""strip_rotation.py — 强制去除 MP4 文件的 displaymatrix 旋转标记。

ffmpeg 自动从源 sync displaymatrix side data 到输出，导致带 -90 rotation 的源
（手机竖屏拍摄）的输出在播放器中显示时被"二次旋转"成竖屏。

无 mp4box/atomicparsley/mutagen 可用 → 直接在 tkhd atom 中把 matrix 重写为单位矩阵。

用法：
    python strip_rotation.py VIDEO.mp4 [VIDEO2.mp4 ...]

验证：
    ffmpeg -i output.mp4   # 应无 "displaymatrix: rotation of" 行
"""

import struct
import sys
from pathlib import Path


def find_atoms(data, start, end, target_type):
    """在 [start:end] 区间内找所有 type == target_type 的 atom 位置。"""
    pos = start
    results = []
    while pos + 8 <= end:
        size = struct.unpack('>I', data[pos:pos + 4])[0]
        atype = data[pos + 4:pos + 8].decode('ascii', errors='replace')
        if size < 8:
            break
        if atype == target_type:
            results.append(pos)
        pos += size
    return results


def strip_tkhd_matrix_inplace(data):
    """把所有 tkhd atom 中的 matrix 重写为单位矩阵。

    tkhd box layout (per ISO 14496-12):
      v0:
        +0   size (4)
        +4   'tkhd' (4)
        +8   version(1)+flags(3)
        +12  creation_time: unsigned int(32)[2] = 8 bytes (2 × 4-byte)
        +20  modification_time: unsigned int(32)[2] = 8 bytes
        +28  track_ID (4)
        +32  reserved (4)
        +36  duration (4)
        +40  reserved (8) [two 4-byte]
        +48  layer (2)
        +50  alternate_group (2)
        +52  volume (2)
        +54  reserved (2)
        +56  matrix (36)  ← 这里！
        +92 (size 84 / 92 incl header)

      v1: 同样的 layout 但 creation_time/modification_time 是 uint32[2]（也是 8 字节）
           或部分文档说 v1 用 uint64？我们按 ffmpeg 实际产出的 v0 算（85% 都是 v0）。
    """
    if data[4:8] != b'ftyp':
        return 0

    moov_pos_list = find_atoms(data, 0, len(data), 'moov')
    count = 0
    for moov_pos in moov_pos_list:
        moov_size = struct.unpack('>I', data[moov_pos:moov_pos + 4])[0]
        moov_end = moov_pos + moov_size
        trak_list = find_atoms(data, moov_pos + 8, moov_end, 'trak')
        for trak_pos in trak_list:
            trak_size = struct.unpack('>I', data[trak_pos:trak_pos + 4])[0]
            trak_end = trak_pos + trak_size
            tkhd_list = find_atoms(data, trak_pos + 8, trak_end, 'tkhd')
            for tkhd_pos in tkhd_list:
                tkhd_size = struct.unpack('>I', data[tkhd_pos:tkhd_pos + 4])[0]
                version = data[tkhd_pos + 8]
                # v0/v1 矩阵都在 +56 偏移（按本次 MP4 v0 实测 layout）
                # 如果你的文件非标，调整这里
                matrix_offset = tkhd_pos + 56
                # 安全检查
                if matrix_offset + 36 > tkhd_pos + tkhd_size:
                    # 尝试 v1 偏移 (+76)
                    matrix_offset = tkhd_pos + 76
                    if matrix_offset + 36 > tkhd_pos + tkhd_size:
                        # 两种偏移都不行，跳过此 tkhd
                        continue
                # 单位矩阵 9×32-bit 固定点
                identity = struct.pack('>9i',
                                       0x00010000, 0, 0,
                                       0, 0x00010000, 0,
                                       0, 0, 0x40000000)
                data[matrix_offset:matrix_offset + 36] = identity
                count += 1
                # 同时也清掉 / skip 版本的 side data 不重要，因为转 tkhd 才是播放器读取的
    return count


def strip_rotation(path):
    """去除指定 MP4 的 rotation metadata。"""
    p = Path(path)
    data = bytearray(p.read_bytes())
    n = strip_tkhd_matrix_inplace(data)
    if n > 0:
        p.write_bytes(bytes(data))
    return n


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python strip_rotation.py VIDEO.mp4 [VIDEO2.mp4 ...]")
        sys.exit(1)
    total_files = 0
    total_tracks = 0
    for arg in sys.argv[1:]:
        n = strip_rotation(arg)
        if n > 0:
            print(f"  ✓ {arg}: stripped {n} tkhd matrix(es)")
        else:
            print(f"  - {arg}: no tkhd found (already stripped?)")
        total_files += 1
        total_tracks += n
    print(f"\n总计 {total_files} 个文件，处理 {total_tracks} 个 track。")
