# -*- coding: utf-8 -*-
"""渲染器测试:看体脂/看围度/趋势/对比/删除回执(2026-08-02 · ticket #9 L5 垂直链路)"""
import os, sys, sqlite3, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import body_composition as bc
import body_measurements as bm
from db import init_db
import pytest


@pytest.fixture
def tmp_db(monkeypatch, tmp_path):
    db_path = tmp_path / 'calorie_data.db'
    init_db(str(db_path))
    monkeypatch.setenv('SKILLS_DB_PATH', str(tmp_path))
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO body_composition (
            date, source, age, sex,
            caliper_chest_mm, caliper_abdominal_mm, caliper_thigh_mm, caliper_tricep_mm,
            caliper_subscapular_mm, caliper_suprailiac_mm, caliper_midaxillary_mm,
            body_fat_pct, note
        ) VALUES ('2026-07-20', 'home_caliper', 30, 'male',
            5, 8, 10, 6, 9, 7, 6, 18.5, '')
    """)
    cur.execute("""
        INSERT INTO body_composition (
            date, source, age, sex,
            caliper_chest_mm, caliper_abdominal_mm, caliper_thigh_mm, caliper_tricep_mm,
            caliper_subscapular_mm, caliper_suprailiac_mm, caliper_midaxillary_mm,
            body_fat_pct, note
        ) VALUES ('2026-07-25', 'gym', 30, 'male',
            5, 8, 10, 6, 9, 7, 6, 17.8, '')
    """)
    cur.execute("""
        INSERT INTO body_measurements (date, waist_cm, hip_cm, chest_cm, note)
        VALUES ('2026-07-20', 85, 95, 100, '')
    """)
    cur.execute("""
        INSERT INTO body_measurements (date, waist_cm, hip_cm, note)
        VALUES ('2026-07-25', 83, 94, '')
    """)
    conn.commit()
    conn.close()
    yield str(db_path)


def _render_module(mod, monkeypatch, tmp_db):
    monkeypatch.setattr(mod, 'TEMPLATE_PATH', tmp_db and mod.TEMPLATE_PATH)
    return mod


def test_composition_view_list(tmp_db, monkeypatch):
    import render_body_composition_view as rv
    c = rv._get_conn()
    try:
        data = rv.build_list(c)
        assert data['mode'] == 'list'
        assert len(data['rows']) == 2
        assert data['current']['body_fat_pct'] == 17.8
        assert len(data['filter']['groups']) == 3
    finally:
        c.close()


def test_composition_view_list_source_filter(tmp_db, monkeypatch):
    import render_body_composition_view as rv
    c = rv._get_conn()
    try:
        data = rv.build_list(c, source='gym')
        assert len(data['rows']) == 1
        assert data['rows'][0]['source'] == 'gym'
    finally:
        c.close()


def test_composition_view_trend_default_latest_source(tmp_db, monkeypatch):
    import render_body_composition_view as rv
    c = rv._get_conn()
    try:
        data = rv.build_trend(c, days=90)
        assert data['mode'] == 'trend'
        assert data['source'] == 'gym'
        assert len(data['rows']) == 1
        assert data['kpi']['avg'] == 17.8
    finally:
        c.close()


def test_composition_view_compare(tmp_db, monkeypatch):
    import render_body_composition_view as rv
    c = rv._get_conn()
    try:
        data = rv.build_compare(c, '2026-07-01', '2026-07-23', '2026-07-24', '2026-07-31', source='home_caliper')
        assert data['mode'] == 'compare'
        assert data['period1']['n'] == 1
        assert data['period1']['avg_pct'] == 18.5
        assert data['period2']['n'] == 0
        assert data['delta'] is None
    finally:
        c.close()


def test_measurements_view_list(tmp_db, monkeypatch):
    import render_body_measurements_view as rv
    c = rv._get_conn()
    try:
        data = rv.build_list(c)
        assert data['mode'] == 'list'
        assert len(data['rows']) == 2
        assert data['rows'][0]['waist_cm'] == 83
    finally:
        c.close()


def test_measurements_view_list_metric_filter(tmp_db, monkeypatch):
    import render_body_measurements_view as rv
    c = rv._get_conn()
    try:
        data = rv.build_list(c, metric='waist-cm')
        assert len(data['rows']) == 2
    finally:
        c.close()


def test_measurements_view_trend(tmp_db, monkeypatch):
    import render_body_measurements_view as rv
    c = rv._get_conn()
    try:
        data = rv.build_trend(c, 'waist-cm', days=90)
        assert data['mode'] == 'trend'
        assert len(data['rows']) == 2
        assert data['kpi']['delta'] == -2.0
    finally:
        c.close()


def test_measurements_view_compare(tmp_db, monkeypatch):
    import render_body_measurements_view as rv
    c = rv._get_conn()
    try:
        data = rv.build_compare(c, '2026-07-20', '2026-07-25')
        assert data['mode'] == 'compare'
        assert data['n_compared'] == 2
        deltas = {d['label']: d['delta'] for d in data['deltas']}
        assert deltas['腰围'] == -2.0
        assert deltas['臀围'] == -1.0
    finally:
        c.close()


def test_delete_receipt_composition(tmp_db, monkeypatch):
    import render_body_delete_receipt as rd
    data = rd.build_delete('composition', 1)
    assert data['status'] == 'ok'
    assert '已删除删体脂' in data['data']['summary']
    # 确认已软删
    conn = sqlite3.connect(tmp_db)
    row = conn.execute('SELECT is_deprecated FROM body_composition WHERE id=1').fetchone()
    assert row[0] == 1
    conn.close()


def test_delete_receipt_measurements(tmp_db, monkeypatch):
    import render_body_delete_receipt as rd
    data = rd.build_delete('measurements', 1)
    assert data['status'] == 'ok'
    conn = sqlite3.connect(tmp_db)
    row = conn.execute('SELECT is_deprecated FROM body_measurements WHERE id=1').fetchone()
    assert row[0] == 1
    conn.close()
