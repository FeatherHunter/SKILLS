#!/usr/bin/env python3
"""exercise_review 单元测试

测试场景：
1. 计划休息日 + 无实绩 → "休息日 / 无计划无实绩"
2. 计划有 + log 空 → "计划有训练但完全未做"
3. 计划无 + log 有 → "计划休息但实做了 N 组"
4. 计划 4 组 + log 4 组 → 完成率 100%
5. 完成率 < 50% → 异常标记
6. 完成率 > 130% → 异常标记
7. 多日范围 → 返回 dict 长度 = 日期数

运行方法：
    cd D:\2Study\StudyNotes\SKILLS\卡路里\scripts
    python -m unittest tests.test_exercise_review
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# 阻止 workout_plan 真实加载（避免 DB 副作用）
workout_plan_mock = types.ModuleType('workout_plan')
workout_plan_mock.get_day_plan = MagicMock()
sys.modules['workout_plan'] = workout_plan_mock


def _make_log_rows(items):
    """构造 exercise_log 查询结果

    items: list of (exercise_type, set_index, reps, load_kg)
    """
    rows = []
    for i, (etype, set_idx, reps, load) in enumerate(items):
        # (id, exercise_type, duration_minutes, calories_burned, set_index, reps, load_kg)
        rows.append((i + 1, etype, 30, 50, set_idx, reps, load))
    return rows


def _mock_db(log_rows):
    """构造 mock DB（cursor.fetchall 返回 log_rows）"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = log_rows
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


def _plan(sessions):
    """构造 get_day_plan 返回值"""
    return {
        'date': '2026-07-13',
        'plan_week': 1,
        'day_of_week': 1,
        'config': None,
        'sessions': sessions,
    }


def _rest_day():
    return _plan([{'session_label': '休息日', 'is_rest_day': 1, 'total_sets': 0, 'movements': []}])


def _train_day(label='上午·臂', total_sets=8):
    return _plan([{'session_label': label, 'is_rest_day': 0, 'total_sets': total_sets, 'movements': []}])


class TestExerciseReview(unittest.TestCase):

    def setUp(self):
        # 每个测试前重置 mock
        sys.modules['workout_plan'].get_day_plan.reset_mock()

    def test_01_rest_day_no_log(self):
        """场景 1: 计划休息日 + 无实绩 → 休息日 / 无计划无实绩"""
        sys.modules['workout_plan'].get_day_plan.return_value = _rest_day()
        from analysis.exercise import exercise_review
        with patch('analysis.exercise._get_db', return_value=_mock_db([])):
            result = exercise_review('2026-07-13', '2026-07-13', silent=True)

        self.assertIn('2026-07-13', result)
        self.assertEqual(result['2026-07-13']['plan_total_sets'], 0)
        self.assertEqual(result['2026-07-13']['actual_total_sets'], 0)
        self.assertEqual(result['2026-07-13']['note'], '休息日 / 无计划无实绩')
        self.assertIsNone(result['2026-07-13']['completion_rate'])
        self.assertEqual(result['2026-07-13']['anomalies'], [])

    def test_02_plan_no_log(self):
        """场景 2: 计划有 + log 空 → 计划有训练但完全未做"""
        sys.modules['workout_plan'].get_day_plan.return_value = _train_day(total_sets=8)
        from analysis.exercise import exercise_review
        with patch('analysis.exercise._get_db', return_value=_mock_db([])):
            result = exercise_review('2026-07-13', '2026-07-13', silent=True)

        self.assertEqual(result['2026-07-13']['plan_total_sets'], 8)
        self.assertEqual(result['2026-07-13']['actual_total_sets'], 0)
        self.assertEqual(result['2026-07-13']['completion_rate'], 0.0)
        self.assertIn('计划有训练但完全未做', result['2026-07-13']['note'])
        self.assertTrue(any('❌' in a for a in result['2026-07-13']['anomalies']))

    def test_03_no_plan_with_log(self):
        """场景 3: 计划无 + log 有 → 计划休息但实做了 N 组"""
        sys.modules['workout_plan'].get_day_plan.return_value = _rest_day()
        from analysis.exercise import exercise_review
        with patch('analysis.exercise._get_db', return_value=_mock_db(_make_log_rows([
            ('俯卧撑', 1, 10, 0),
            ('俯卧撑', 2, 10, 0),
        ]))):
            result = exercise_review('2026-07-13', '2026-07-13', silent=True)

        self.assertEqual(result['2026-07-13']['plan_total_sets'], 0)
        self.assertEqual(result['2026-07-13']['actual_total_sets'], 2)
        self.assertIn('计划休息但实做了 2 组', result['2026-07-13']['note'])
        self.assertTrue(any('⚠️' in a for a in result['2026-07-13']['anomalies']))

    def test_04_normal_100_percent(self):
        """场景 4: 计划 4 组 + log 4 组 → 完成率 100%"""
        sys.modules['workout_plan'].get_day_plan.return_value = _train_day(total_sets=4)
        from analysis.exercise import exercise_review
        with patch('analysis.exercise._get_db', return_value=_mock_db(_make_log_rows([
            ('哑铃弯举', 1, 10, 10),
            ('哑铃弯举', 2, 10, 10),
            ('哑铃弯举', 3, 10, 10),
            ('哑铃弯举', 4, 10, 10),
        ]))):
            result = exercise_review('2026-07-13', '2026-07-13', silent=True)

        self.assertEqual(result['2026-07-13']['plan_total_sets'], 4)
        self.assertEqual(result['2026-07-13']['actual_total_sets'], 4)
        self.assertEqual(result['2026-07-13']['completion_rate'], 100.0)
        self.assertEqual(result['2026-07-13']['anomalies'], [])

    def test_05_low_completion(self):
        """场景 5: 完成率 < 50% → 异常"""
        sys.modules['workout_plan'].get_day_plan.return_value = _train_day(total_sets=10)
        from analysis.exercise import exercise_review
        with patch('analysis.exercise._get_db', return_value=_mock_db(_make_log_rows([
            ('哑铃弯举', 1, 10, 10),
        ]))):
            result = exercise_review('2026-07-13', '2026-07-13', silent=True)

        self.assertEqual(result['2026-07-13']['plan_total_sets'], 10)
        self.assertEqual(result['2026-07-13']['actual_total_sets'], 1)
        self.assertEqual(result['2026-07-13']['completion_rate'], 10.0)
        self.assertTrue(any('完成率仅 10%' in a for a in result['2026-07-13']['anomalies']))

    def test_06_over_completion(self):
        """场景 6: 完成率 > 130% → 异常"""
        sys.modules['workout_plan'].get_day_plan.return_value = _train_day(total_sets=5)
        from analysis.exercise import exercise_review
        with patch('analysis.exercise._get_db', return_value=_mock_db(_make_log_rows([
            ('哑铃弯举', i, 10, 10) for i in range(1, 8)
        ]))):
            result = exercise_review('2026-07-13', '2026-07-13', silent=True)

        self.assertEqual(result['2026-07-13']['plan_total_sets'], 5)
        self.assertEqual(result['2026-07-13']['actual_total_sets'], 7)
        self.assertEqual(result['2026-07-13']['completion_rate'], 140.0)
        self.assertTrue(any('超额完成' in a for a in result['2026-07-13']['anomalies']))

    def test_07_multi_day_range(self):
        """场景 7: 多日范围 → 返回 dict 长度 = 日期数"""
        # 7 天范围，get_day_plan 返回同一 plan
        sys.modules['workout_plan'].get_day_plan.return_value = _train_day(total_sets=4)
        from analysis.exercise import exercise_review
        with patch('analysis.exercise._get_db', return_value=_mock_db([])):
            result = exercise_review('2026-07-07', '2026-07-13', silent=True)

        # 7/7, 7/8, 7/9, 7/10, 7/11, 7/12, 7/13 = 7 天
        self.assertEqual(len(result), 7)
        self.assertIn('2026-07-07', result)
        self.assertIn('2026-07-13', result)

    def test_08_silent_mode(self):
        """场景 8: silent=True 不打印"""
        import io
        from contextlib import redirect_stdout

        sys.modules['workout_plan'].get_day_plan.return_value = _rest_day()
        from analysis.exercise import exercise_review
        with patch('analysis.exercise._get_db', return_value=_mock_db([])):
            buf = io.StringIO()
            with redirect_stdout(buf):
                exercise_review('2026-07-13', '2026-07-13', silent=True)
            # silent=True 时不应有 print 输出
            self.assertEqual(buf.getvalue(), '')

        # silent=False（默认）应打印
        with patch('analysis.exercise._get_db', return_value=_mock_db([])):
            buf = io.StringIO()
            with redirect_stdout(buf):
                exercise_review('2026-07-13', '2026-07-13')
            self.assertIn('训练复盘', buf.getvalue())

    def test_09_unstarted_plan(self):
        """场景 9: 计划未开始（date < plan.start_date）→ 计划尚未开始"""
        sys.modules['workout_plan'].get_day_plan.return_value = {
            'date': '2026-07-01',  # 早于 plan start_date 2026-07-13
            'plan_week': None,
            'day_of_week': 3,
            'config': {'start_date': '2026-07-13'},
            'sessions': [],
            'unstarted': True,
        }
        from analysis.exercise import exercise_review
        with patch('analysis.exercise._get_db', return_value=_mock_db([])):
            result = exercise_review('2026-07-01', '2026-07-01', silent=True)

        self.assertEqual(result['2026-07-01']['note'], '计划尚未开始(起始 2026-07-13)')
        self.assertIsNone(result['2026-07-01']['completion_rate'])
        self.assertEqual(result['2026-07-01']['anomalies'], [])

    def test_10_cli_resolve_range(self):
        """场景 10: CLI resolve_range 解析（6 个参数）"""
        from exercise_review import resolve_range
        from datetime import date, timedelta

        today = date.today()
        today_str = today.strftime('%Y-%m-%d')
        yesterday_str = (today - timedelta(days=1)).strftime('%Y-%m-%d')
        day_before_str = (today - timedelta(days=2)).strftime('%Y-%m-%d')

        # --today
        self.assertEqual(resolve_range(_ns(today=True)), (today_str, today_str))
        # --yesterday
        self.assertEqual(resolve_range(_ns(yesterday=True)), (yesterday_str, yesterday_str))
        # --day-before-yesterday
        self.assertEqual(resolve_range(_ns(day_before_yesterday=True)), (day_before_str, day_before_str))
        # --days 7
        expected_start = (today - timedelta(days=6)).strftime('%Y-%m-%d')
        self.assertEqual(resolve_range(_ns(days=7)), (expected_start, today_str))
        # --start --end
        self.assertEqual(resolve_range(_ns(start='2026-07-01', end='2026-07-13')), ('2026-07-01', '2026-07-13'))
        # --start only
        self.assertEqual(resolve_range(_ns(start='2026-07-13')), ('2026-07-13', '2026-07-13'))
        # 默认（无参数 → 今天）
        self.assertEqual(resolve_range(_ns()), (today_str, today_str))

    def test_11_error_date_format(self):
        """场景 11: 错误日期格式 → ValueError"""
        from analysis.exercise import exercise_review
        with self.assertRaises(ValueError):
            exercise_review('2026/07/13', '2026/07/13', silent=True)


def _ns(**kwargs):
    """构造 argparse Namespace 模拟对象(带所有参数默认值,避免 resolve_range 访问不到属性)"""
    from argparse import Namespace
    defaults = {
        'start': None, 'end': None,
        'today': False, 'yesterday': False, 'day_before_yesterday': False,
        'days': None,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


if __name__ == '__main__':
    unittest.main()
