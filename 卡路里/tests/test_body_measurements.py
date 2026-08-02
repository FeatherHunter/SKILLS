import os, sys, sqlite3, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import body_measurements as bm
from db import init_db
from validators import ValidationError
import pytest


@pytest.fixture
def tmp_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
    init_db(path)
    monkeypatch.setattr(bm, 'DB_PATH', path)
    yield path
    os.unlink(path)


def test_add_no_metrics_fails(tmp_db):
    args = bm.parse_args(['--date', '2026-07-25'])
    with pytest.raises(ValidationError):
        bm.cmd_add(args)


def test_add_one_metric_succeeds(tmp_db):
    args = bm.parse_args(['--date', '2026-07-25', '--waist-cm', '85'])
    result = bm.cmd_add(args)
    assert result['status'] == 'ok'
    assert result['data']['id'] >= 1


def test_add_all_metrics_succeeds(tmp_db):
    args = bm.parse_args([
        '--date', '2026-07-25',
        '--chest-cm', '95', '--waist-cm', '85', '--abdomen-cm', '88',
        '--hip-cm', '95', '--left-thigh-cm', '55', '--right-thigh-cm', '55',
        '--left-calf-cm', '38', '--right-calf-cm', '38',
        '--left-arm-cm', '32', '--right-arm-cm', '32',
        '--left-forearm-cm', '28', '--right-forearm-cm', '28',
        '--shoulder-cm', '110',
    ])
    result = bm.cmd_add(args)
    assert result['status'] == 'ok'


def test_list_returns(tmp_db):
    bm.cmd_add(bm.parse_args(['--date', '2026-07-25', '--waist-cm', '85']))
    args = bm.parse_args(['--days', '30'])
    result = bm.cmd_list(args)
    assert result['status'] == 'ok'
    assert len(result['data']) >= 1

def test_list_returns_13_columns(tmp_db):
    bm.cmd_add(bm.parse_args(['--date', '2026-07-20', '--waist-cm', '85', '--hip-cm', '95']))
    result = bm.cmd_list(bm.parse_args(['list', '--days', '30']))
    assert result['status'] == 'ok'
    row = result['data'][0]
    assert 'waist_cm' in row and 'chest_cm' in row and 'shoulder_cm' in row


def test_list_metric_filter(tmp_db):
    bm.cmd_add(bm.parse_args(['--date', '2026-07-20', '--waist-cm', '85']))
    bm.cmd_add(bm.parse_args(['--date', '2026-07-25', '--hip-cm', '94']))
    result = bm.cmd_list(bm.parse_args(['list', '--days', '30', '--metric', 'waist-cm']))
    assert result['status'] == 'ok'
    assert len(result['data']) == 1
    assert result['data'][0]['waist_cm'] == 85.0


def test_compare_two_dates(tmp_db):
    bm.cmd_add(bm.parse_args(['--date', '2026-07-20', '--waist-cm', '85', '--hip-cm', '95']))
    bm.cmd_add(bm.parse_args(['--date', '2026-07-25', '--waist-cm', '83', '--hip-cm', '94']))
    result = bm.cmd_compare(bm.parse_args(['--date1', '2026-07-20', '--date2', '2026-07-25']))
    assert result['status'] == 'ok'
    d = result['data']
    assert d['deltas']['waist_cm']['delta'] == -2.0
    assert d['n_compared'] == 2
