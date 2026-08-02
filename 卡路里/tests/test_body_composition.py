import os, sys, sqlite3, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import body_composition as bc
from db import init_db
import pytest


@pytest.fixture
def tmp_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
    init_db(path)
    monkeypatch.setattr(bc, 'DB_PATH', path)
    yield path
    os.unlink(path)


def _valid_args(**overrides):
    base = dict(
        date='2026-07-25', source='home_caliper',
        age=30, sex='male',
        caliper_chest_mm=5, caliper_abdominal_mm=10,
        caliper_thigh_mm=15, caliper_tricep_mm=8,
        caliper_subscapular_mm=10, caliper_suprailiac_mm=8,
        caliper_midaxillary_mm=7, body_fat_pct=18.0,
        calculated_at=None, note='', as_dict=False,
    )
    base.update(overrides)
    return bc.parse_args(_args_to_list(base))


def _args_to_list(d):
    """{'date': 'X', 'source': 'Y'} → ['--date', 'X', '--source', 'Y', ...]"""
    out = []
    for k, v in d.items():
        if v is None: continue
        cli = k.replace('_', '-')
        out.append(f'--{cli}')
        if not isinstance(v, bool):
            out.append(str(v))
    return out


def test_add_with_7_points_succeeds(tmp_db):
    result = bc.cmd_add(_valid_args())
    assert result['status'] == 'ok'
    assert result['data']['id'] >= 1


def test_add_missing_caliper_fails(tmp_db):
    args = _valid_args()
    args.caliper_chest_mm = None
    from validators import ValidationError
    with pytest.raises(ValidationError):
        bc.cmd_add(args)


def test_list_returns_recent(tmp_db):
    bc.cmd_add(_valid_args())
    args = bc.parse_args(['trend', '--days', '30'])
    result = bc.cmd_list(args)
    assert result['status'] == 'ok'
    assert len(result['data']) >= 1


def test_delete_soft_deletes(tmp_db):
    bc.cmd_add(_valid_args())
    rid = bc.cmd_list(bc.parse_args(['--days', '30']))['data'][0]['id']
    result = bc.cmd_delete(bc.parse_args(['--id', str(rid)]))
    assert result['status'] == 'ok'
    conn = sqlite3.connect(tmp_db); c = conn.cursor()
    row = c.execute('SELECT is_deprecated FROM body_composition WHERE id=?', (rid,)).fetchone()
    assert row[0] == 1
    conn.close()


def test_as_dict_flag_works():
    args = bc.parse_args(['--as-dict'])
    assert args.as_dict is True

def test_list_source_filter(tmp_db):
    bc.cmd_add(_valid_args(date='2026-07-20'))
    bc.cmd_add(_valid_args(date='2026-07-25', source='gym'))
    args = bc.parse_args(['list', '--days', '30', '--source', 'gym'])
    result = bc.cmd_list(args)
    assert result['status'] == 'ok'
    assert len(result['data']) == 1
    assert result['data'][0]['source'] == 'gym'


def test_trend_default_uses_latest_source(tmp_db):
    bc.cmd_add(_valid_args(date='2026-07-20'))
    bc.cmd_add(_valid_args(date='2026-07-25', source='gym'))
    args = bc.parse_args(['trend', '--days', '30'])
    result = bc.cmd_trend(args)
    assert result['status'] == 'ok'
    assert 'source=gym' in result['message']


def test_trend_explicit_source(tmp_db):
    bc.cmd_add(_valid_args(date='2026-07-20'))
    bc.cmd_add(_valid_args(date='2026-07-25', source='gym'))
    args = bc.parse_args(['trend', '--days', '30', '--source', 'home_caliper'])
    result = bc.cmd_trend(args)
    assert result['status'] == 'ok'
    assert 'source=home_caliper' in result['message']
    assert len(result['data']) == 1


def test_compare_two_periods(tmp_db):
    bc.cmd_add(_valid_args(date='2026-07-10', body_fat_pct=20.0))
    bc.cmd_add(_valid_args(date='2026-07-20', body_fat_pct=19.0))
    bc.cmd_add(_valid_args(date='2026-07-28', body_fat_pct=18.0))
    args = bc.parse_args(['--start1', '2026-07-01', '--end1', '2026-07-15',
                          '--start2', '2026-07-21', '--end2', '2026-07-31'])
    result = bc.cmd_compare(args)
    assert result['status'] == 'ok'
    d = result['data']
    assert d['period1']['n'] == 1 and d['period1']['avg_pct'] == 20.0
    assert d['period2']['n'] == 1 and d['period2']['avg_pct'] == 18.0
    assert d['delta'] == -2.0


def test_add_gym_source_succeeds(tmp_db):
    result = bc.cmd_add(_valid_args(source='gym'))
    assert result['status'] == 'ok'
