"""身体数据校验(V1.0 §02 第 ④ 可约束)

早失败 + 错误信息含字段名 + 当前值 + 期望值 + 怎么修。
无 --force 跳过通道。
"""
import re

from source_constants import SOURCE_CHOICES

ISO_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

CALIPER_MIN_MM = 0.0
CALIPER_MAX_MM = 100.0
BODY_FAT_PCT_MIN = 0.0
BODY_FAT_PCT_MAX = 60.0
CALIPER_FIELDS = [
    'caliper_chest_mm', 'caliper_abdominal_mm', 'caliper_thigh_mm',
    'caliper_tricep_mm', 'caliper_subscapular_mm', 'caliper_suprailiac_mm',
    'caliper_midaxillary_mm',
]
MEASUREMENT_FIELDS = [
    'chest_cm', 'waist_cm', 'abdomen_cm', 'hip_cm',
    'left_thigh_cm', 'right_thigh_cm',
    'left_calf_cm', 'right_calf_cm',
    'left_arm_cm', 'right_arm_cm',
    'left_forearm_cm', 'right_forearm_cm',
    'shoulder_cm',
]
MEASUREMENT_BOUNDS = {
    'chest_cm': (20, 200), 'waist_cm': (20, 200), 'abdomen_cm': (20, 200), 'hip_cm': (20, 200),
    'shoulder_cm': (20, 200),
    'left_thigh_cm': (10, 100), 'right_thigh_cm': (10, 100),
    'left_calf_cm': (10, 80), 'right_calf_cm': (10, 80),
    'left_arm_cm': (10, 60), 'right_arm_cm': (10, 60),
    'left_forearm_cm': (10, 50), 'right_forearm_cm': (10, 50),
}


class ValidationError(ValueError):
    pass


def _fail(field, value, expected, fix):
    raise ValidationError(
        f"field={field}, value={value!r}, expected={expected}, fix={fix}"
    )


def _is_valid_iso_date(s):
    return bool(s and ISO_DATE_RE.match(s))


def _caliper_cli_name(f):
    name = f.replace('_mm', '')
    parts = name.split('_')
    return '-'.join(parts)


def validate_composition_input(args) -> None:
    if not _is_valid_iso_date(args.date):
        _fail('date', args.date, 'YYYY-MM-DD', 'fix: --date 2026-07-25')
    if args.source not in SOURCE_CHOICES:
        _fail('source', args.source, SOURCE_CHOICES,
              f'fix: --source {" --source ".join(SOURCE_CHOICES)}')
    for f in CALIPER_FIELDS:
        v = getattr(args, f, None)
        if v is None:
            _fail(f, v, f'(0, 100)mm · 7 个皮褶必填', f'fix: --{_caliper_cli_name(f)} 5')
        if not (CALIPER_MIN_MM < v < CALIPER_MAX_MM):
            _fail(f, v, f'({CALIPER_MIN_MM}, {CALIPER_MAX_MM})mm (exclusive)', f'fix: --{_caliper_cli_name(f)} 5')
    bf = getattr(args, 'body_fat_pct', None)
    if bf is None:
        _fail('body_fat_pct', bf, f'[{BODY_FAT_PCT_MIN}, {BODY_FAT_PCT_MAX}]', 'fix: 自动算或 --body-fat-pct 18')
    if not (BODY_FAT_PCT_MIN < bf < BODY_FAT_PCT_MAX):
        _fail('body_fat_pct', bf, f'[{BODY_FAT_PCT_MIN}, {BODY_FAT_PCT_MAX}] (exclusive)', 'fix: --body-fat-pct 18')


def validate_measurement_input(args) -> None:
    if not _is_valid_iso_date(args.date):
        _fail('date', args.date, 'YYYY-MM-DD', 'fix: --date 2026-07-25')
    filled = []
    for f in MEASUREMENT_FIELDS:
        v = getattr(args, f, None)
        if v is not None:
            lo, hi = MEASUREMENT_BOUNDS[f]
            if not (lo <= v <= hi):
                _fail(f, v, f'[{lo}, {hi}]cm', f'fix: --{_caliper_cli_name(f)} 85')
            filled.append(f)
    if not filled:
        _fail('围度', 'empty', '≥ 1 个(记录级必填)',
               'fix: --waist-cm 85 或 --hip-cm 95 至少 1 个')