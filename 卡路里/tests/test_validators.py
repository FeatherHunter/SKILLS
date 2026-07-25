#!/usr/bin/env python3
"""validators.py 单元测试 — Task 3 规则层校验

V1.0 §02 第 ④ 可约束:
  - 早失败 + 错误信息含字段名
  - source 白名单(消除魔法字符串)
  - 围度范围 + 记录级必填(≥1 围度)
"""

import os
import sys

import pytest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

from validators import validate_composition_input, validate_measurement_input, ValidationError


def _composition_args(**overrides):
    base = {
        'date': '2026-07-25', 'source': 'home_caliper',
        'caliper_chest_mm': 5, 'caliper_abdominal_mm': 10,
        'caliper_thigh_mm': 15, 'caliper_tricep_mm': 8,
        'caliper_subscapular_mm': 10, 'caliper_suprailiac_mm': 8,
        'caliper_midaxillary_mm': 7, 'body_fat_pct': 18.0,
    }
    base.update(overrides)
    return type('A', (), base)()


def test_composition_no_date_fails():
    """早失败:date 缺失"""
    args = _composition_args(date=None)
    with pytest.raises(ValidationError) as e:
        validate_composition_input(args)
    assert 'date' in str(e.value)


def test_composition_invalid_source_fails():
    """source 白名单校验(消除魔法字符串)"""
    args = _composition_args(source='bogus_source')
    with pytest.raises(ValidationError) as e:
        validate_composition_input(args)
    assert 'source' in str(e.value)


def test_composition_caliper_out_of_range_fails():
    """7 皮褶值范围(0, 100)mm"""
    args = _composition_args(caliper_chest_mm=150)
    with pytest.raises(ValidationError) as e:
        validate_composition_input(args)
    assert 'caliper_chest_mm' in str(e.value)


def test_composition_valid_passes():
    args = _composition_args()
    validate_composition_input(args)


def test_measurement_no_metrics_fails():
    """记录级必填:≥1 围度"""
    args = type('A', (), {
        'date': '2026-07-25',
        'chest_cm': None, 'waist_cm': None, 'abdomen_cm': None, 'hip_cm': None,
        'shoulder_cm': None,
        'left_thigh_cm': None, 'right_thigh_cm': None,
        'left_calf_cm': None, 'right_calf_cm': None,
        'left_arm_cm': None, 'right_arm_cm': None,
        'left_forearm_cm': None, 'right_forearm_cm': None,
    })()
    with pytest.raises(ValidationError) as e:
        validate_measurement_input(args)
    assert '围度' in str(e.value)


def test_measurement_one_metric_passes():
    args = type('A', (), {
        'date': '2026-07-25', 'waist_cm': 85,
        'chest_cm': None, 'abdomen_cm': None, 'hip_cm': None,
        'shoulder_cm': None,
        'left_thigh_cm': None, 'right_thigh_cm': None,
        'left_calf_cm': None, 'right_calf_cm': None,
        'left_arm_cm': None, 'right_arm_cm': None,
        'left_forearm_cm': None, 'right_forearm_cm': None,
    })()
    validate_measurement_input(args)