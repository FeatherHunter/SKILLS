# -*- coding: utf-8 -*-
"""验证：单独跑 test_exercise_review_volume.py 时 SKILLS_DB_PATH 被隔离"""
import os
import pytest


def test_isolated_when_solo(temp_db):
    """单独跑本文件时 temp_db 也必须激活（依赖 seed_volume -> temp_db）"""
    from db import find_db_path
    from pathlib import Path
    skill = Path(__file__).resolve().parent.parent
    resolved = find_db_path(skill, 'calorie_data.db')
    # 关键断言：解析到的 DB 必须指向 temp_db 所在目录（临时），而非生产 D:\2Study\StudyNotes\.db
    assert str(resolved).replace('\\', '/') != 'D:/2Study/StudyNotes/.db/calorie_data.db', \
        f'隔离未生效！解析到生产库: {resolved}'
    assert str(temp_db).replace('\\', '/') == str(resolved).replace('\\', '/'), \
        f'解析不一致: temp={temp_db} resolved={resolved}'
    print(f'OK 隔离生效: {resolved}')
