import struct
path = r'D:\2Study\StudyNotes\2026\自媒体\DAY2\.zhijian_work\test_full.mp4'
data = open(path, 'rb').read()
print(f'Total size: {len(data)}')
print(f'First 32 bytes: {data[:32].hex()}')
print(f'File type at 4: {data[4:8]}')

# Parse atoms recursively
def parse(pos, depth=0):
    while pos < len(data) - 8:
        size = struct.unpack('>I', data[pos:pos+4])[0]
        atype = data[pos+4:pos+8].decode('ascii', errors='replace')
        ind = '  ' * depth
        if size == 0:
            print(f'{ind}pos {pos}: size=0 type={atype!r} (extends to end of file)')
            return
        if size < 8 or pos + size > len(data):
            print(f'{ind}pos {pos}: size={size} type={atype!r} (invalid)')
            return
        print(f'{ind}pos {pos}: size={size} type={atype!r}')
        # Recurse into container atoms
        if atype in ('moov', 'trak', 'mdia', 'minf', 'stbl', 'edts', 'dinf', 'udta'):
            parse(pos + 8, depth + 1)
        elif atype == 'tkhd':
            tkhd_end = pos + size
            print(f'{ind}  [tkhd data: {data[pos+8:pos+32].hex()}]')
            # Show matrix region
            # version byte at pos+8
            v = data[pos+8]
            if v == 0:
                mo = pos + 60
            else:
                mo = pos + 68
            matrix_bytes = data[mo:mo+36]
            print(f'{ind}  version={v}, matrix at offset {mo}: {matrix_bytes.hex()}')
            matrix_vals = struct.unpack('>9i', matrix_bytes)
            print(f'{ind}  matrix: {matrix_vals}')
        pos += size

parse(0)
