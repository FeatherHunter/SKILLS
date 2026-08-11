# -*- coding: utf-8 -*-
"""切片逻辑单元测试:不依赖网络,不调用 mmx。"""
import os
import sys
import tempfile

import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from eye import slice_image, _region_label  # noqa: E402


@pytest.fixture()
def sample_img(tmp_path):
    """造一张 1000x800 的测试图。"""
    img = Image.new("RGB", (1000, 800), (200, 200, 200))
    p = tmp_path / "sample.png"
    img.save(p)
    return str(p)


def test_slice_3x3_count(sample_img, tmp_path):
    tiles = slice_image(sample_img, str(tmp_path), grid=3, target=1024, overlap=0.12)
    assert len(tiles) == 9
    names = {t["name"] for t in tiles}
    assert names == {f"tile_{r}_{c}.png" for r in (1, 2, 3) for c in (1, 2, 3)}


def test_slice_1x1_full(sample_img, tmp_path):
    tiles = slice_image(sample_img, str(tmp_path), grid=1, target=512, overlap=0)
    assert len(tiles) == 1
    assert tiles[0]["x"] == 0 and tiles[0]["y"] == 0


def test_slice_tiles_are_files(sample_img, tmp_path):
    tiles = slice_image(sample_img, str(tmp_path), grid=2, target=1024, overlap=0.1)
    for t in tiles:
        assert os.path.isfile(t["path"])


def test_slice_target_size(sample_img, tmp_path):
    """放大后最长边应为 target。"""
    tiles = slice_image(sample_img, str(tmp_path), grid=3, target=1024, overlap=0.12)
    for t in tiles:
        with Image.open(t["path"]) as im:
            assert max(im.size) == 1024


def test_slice_overlap_nonzero(sample_img, tmp_path):
    """有重叠时,相邻切片 x 起点之差应小于无重叠步长。"""
    tiles = slice_image(sample_img, str(tmp_path), grid=3, target=512, overlap=0.2)
    by = {t["name"]: t for t in tiles}
    step_no_overlap = 1000 / 3
    for c in (1, 2):
        a = by[f"tile_1_{c}.png"]["x"]
        b = by[f"tile_1_{c+1}.png"]["x"]
        assert 0 < (b - a) < step_no_overlap


def test_slice_invalid_grid(sample_img, tmp_path):
    with pytest.raises(SystemExit):
        slice_image(sample_img, str(tmp_path), grid=0, target=512, overlap=0)


def test_slice_invalid_overlap(sample_img, tmp_path):
    with pytest.raises(SystemExit):
        slice_image(sample_img, str(tmp_path), grid=2, target=512, overlap=0.6)


def test_region_label():
    grid = 3
    assert _region_label({"name": "tile_1_1.png"}, grid) == "上左区(第1行第1列)"
    assert _region_label({"name": "tile_1_2.png"}, grid) == "上中区(第1行第2列)"
    assert _region_label({"name": "tile_2_2.png"}, grid) == "中中区(第2行第2列)"
    assert _region_label({"name": "tile_3_3.png"}, grid) == "下右区(第3行第3列)"
    assert _region_label({"name": "tile_1_1.png"}, 1) == "全景"
