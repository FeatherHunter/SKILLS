"""直接改 mp4 tkhd matrix atom"""
import struct
from pathlib import Path

def patch_mp4_rotation(filepath: Path, target_rotation: int = 0):
    """在 mp4 文件里找 tkhd atom 并修改 matrix 字段。

    mp4 box 格式: [size(4 bytes)][type(4 bytes)][data]
    tkhd (track header) 包含 display matrix (36 bytes after track_id)
    """
    data = bytearray(filepath.read_bytes())
    size = len(data)

    # 遍历所有 box 找 tkhd
    offset = 0
    patched = 0
    while offset < size:
        if offset + 8 > size:
            break
        box_size = struct.unpack('>I', data[offset:offset+4])[0]
        box_type = data[offset+4:offset+8].decode('ascii', errors='ignore')

        if box_size == 0:
            break

        if box_type == 'tkhd':
            # tkhd 结构 (version 0):
            #   version(1) + flags(3) + creation(4) + modification(4) +
            #   track_id(4) + reserved(4) + duration(4) + reserved(8) +
            #   layer(2) + alternate_group(2) + volume(2) + reserved(2) +
            #   matrix(36) + width(4) + height(4)
            # 矩阵位置: offset + 8 + 4(version+flags) + 8(creation+modification) +
            #   4(track_id) + 4(reserved) + 4(duration) + 8(reserved) +
            #   2(layer) + 2(alt_group) + 2(volume) + 2(reserved)
            # = offset + 8 + 4 + 8 + 4 + 4 + 4 + 8 + 2 + 2 + 2 + 2 = offset + 48
            matrix_offset = offset + 8 + 4 + 8 + 4 + 4 + 4 + 8 + 2 + 2 + 2 + 2
            # matrix 是 9 个 32-bit fixed point 值 (36 bytes)
            # 单位矩阵 + rotation: 给 identity 旋转 target_rotation
            # 简化: 直接清零 matrix（identity）
            identity_matrix = bytes([
                0x00, 0x01, 0x00, 0x00,  # 1.0
                0x00, 0x00, 0x00, 0x00,  # 0
                0x00, 0x00, 0x00, 0x00,  # 0
                0x00, 0x00, 0x00, 0x00,  # 0
                0x00, 0x01, 0x00, 0x00,  # 1.0
                0x00, 0x00, 0x00, 0x00,  # 0
                0x00, 0x00, 0x00, 0x00,  # 0
                0x00, 0x00, 0x00, 0x00,  # 0
                0x40, 0x00, 0x00, 0x00,  # 1.0 (16.16 fixed)
            ])
            data[matrix_offset:matrix_offset+36] = identity_matrix
            patched += 1
            print(f'  patched tkhd at offset {offset}')

        # Container boxes (moov/trak/mdia...) 递归
        if box_type in ('moov', 'trak', 'mdia', 'minf', 'stbl', 'udta', 'edts'):
            offset += 8  # 进入 container
            continue

        if box_size > 0:
            offset += box_size

    if patched > 0:
        filepath.write_bytes(bytes(data))
        return True
    return False


if __name__ == "__main__":
    import sys
    f = Path(sys.argv[1])
    print(f'patching: {f}')
    if patch_mp4_rotation(f, 0):
        print(f'✓ patched, size now {f.stat().st_size}')
    else:
        print(f'⚠️ no tkhd found')