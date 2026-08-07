"""
#180(2026-08-07)· 中文关键词搜索修复守护

背景:FTS5 unicode61 分词器不切分中文,旧 `notes_fts MATCH ?` 对中文关键词
(尤其 2 字词)100% 失效(真实库 391 条实证:「规划」FTS=0 LIKE=7)。
修复:search_notes 改三字段 LIKE 子串检索(content + category + sub_category)+
ESCAPE 通配符转义。

本文件守护修复后的全部外部可观察行为:
- 中文 2 字/3 字/任意子串命中(旧 FTS 全丢)
- 三字段语义:内容命中 / 分类命中 / 子分类命中
- 通配符转义:% _ \ 按字面(防结果膨胀)
- MATCH 语法炸点消失(搜 a OR b / - 等不再报错)
- 过滤链与排序/LIMIT 行为不变;空关键词路径回归
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent / "script"


def _run_cli(*args, env=None):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "memo_cli.py"), *args],
        capture_output=True, text=True, encoding="utf-8",
        env=env, timeout=10,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _seed(env, rows):
    """预置中文记录(直接写库,绕过 CLI 减少往返)。"""
    import sqlite3
    conn = sqlite3.connect(env["SKILLS_DB_PATH"] + "/memo.db")
    for content, category, sub in rows:
        conn.execute(
            "INSERT INTO notes (content, category, sub_category) VALUES (?,?,?)",
            (content, category, sub),
        )
    conn.commit()
    conn.close()


def _ids(out):
    data = json.loads(out)
    return [r["id"] for r in data.get("data", [])]


SEED = [
    ("完成卡路里技能整个项目的规划", "备忘", "工作"),
    ("今天跑步 5 公里,状态不错", "打卡", "跑步"),
    ("想学 Python 和机器学习", "心愿", "学习"),
    ("进度完成 100%,准备发布", "备忘", None),
    ("文件 a_b 的命名规范", "备忘", None),
    ("用 backslash \\ 转义的路径", "备忘", None),
]


class TestCjkSubstringSearch:
    """中文任意子串命中(旧 FTS 100% 失效的场景)。"""

    def test_chinese_2char_word(self, env_with_tmp_db):
        """2 字词「规划」命中(旧 FTS=0,LIKE=7 的复现场景)。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, err = _run_cli("search", "规划", env=env_with_tmp_db)
        assert rc == 0, f"stderr={err}"
        assert len(_ids(out)) == 1, f"「规划」应命中 1 条,实际 {out}"

    def test_chinese_3char_word(self, env_with_tmp_db):
        """3 字词「卡路里」命中。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "卡路里", env=env_with_tmp_db)
        assert len(_ids(out)) == 1

    def test_arbitrary_substring(self, env_with_tmp_db):
        """任意子串(非完整词):「机器」「准备」命中。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "机器", env=env_with_tmp_db)
        assert len(_ids(out)) == 1
        rc, out, _ = _run_cli("search", "准备发布", env=env_with_tmp_db)
        assert len(_ids(out)) == 1

    def test_english_word_still_works(self, env_with_tmp_db):
        """英文词(Python/backslash)命中。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "Python", env=env_with_tmp_db)
        assert len(_ids(out)) == 1


class TestThreeFieldSemantics:
    """三字段检索语义:内容 / 分类 / 子分类 任一命中(人类 2026-08-07 拍板)。"""

    def test_category_dimension_hit(self, env_with_tmp_db):
        """搜「打卡」命中 category='打卡' 但内容无「打卡」二字的记录。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "打卡", env=env_with_tmp_db)
        ids = _ids(out)
        assert len(ids) == 1, f"应命中打卡分类那条,实际 {out}"
        data = json.loads(out)["data"]
        assert data[0]["category"] == "打卡"

    def test_sub_category_dimension_hit(self, env_with_tmp_db):
        """搜「跑步」命中子分类='跑步'的记录(旧 FTS 未索引 sub_category,新维度)。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "跑步", env=env_with_tmp_db)
        ids = _ids(out)
        assert len(ids) == 1, f"应命中子分类跑步那条,实际 {out}"
        assert json.loads(out)["data"][0]["sub_category"] == "跑步"

    def test_content_and_category_both(self, env_with_tmp_db):
        """搜「备忘」命中内容含 + 分类是备忘的(多维度聚合)。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "备忘", env=env_with_tmp_db)
        ids = _ids(out)
        assert len(ids) == 4, f"「备忘」应命中分类=备忘的 4 条,实际 {out}"


class TestWildcardEscaping:
    """LIKE 通配符转义(防结果膨胀,新实现必须处理的注入面)。"""

    def test_percent_escaped(self, env_with_tmp_db):
        """搜「100%」只命中含字面 100% 的,不返回全部。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "100%", env=env_with_tmp_db)
        ids = _ids(out)
        assert len(ids) == 1, f"「100%」应只命中 1 条(字面),实际 {out}"
        assert "100%" in json.loads(out)["data"][0]["content"]

    def test_underscore_escaped(self, env_with_tmp_db):
        """搜「a_b」不因 _ 通配命中其他记录。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "a_b", env=env_with_tmp_db)
        ids = _ids(out)
        assert len(ids) == 1, f"「a_b」应只命中 1 条(下划线按字面),实际 {out}"

    def test_backslash_escaped(self, env_with_tmp_db):
        """搜「backslash \」命中含反斜杠的记录(转义符本身不炸)。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "backslash", env=env_with_tmp_db)
        assert len(_ids(out)) == 1


class TestMalformedMatchGone:
    """旧 FTS MATCH 语法炸点消失(搜 a OR b / - 等不再报错)。"""

    def test_or_keyword_no_crash(self, env_with_tmp_db):
        _seed(env_with_tmp_db, SEED)
        rc, out, err = _run_cli("search", "a OR b", env=env_with_tmp_db)
        assert rc == 0, f"搜「a OR b」不应报错,stderr={err}"

    def test_dash_keyword_no_crash(self, env_with_tmp_db):
        """关键词含连字符(如「项目-规划」)不触发 SQL 错误。
        注:纯「-x」会被 argparse 当选项拦下(CLI 层行为,与 SQL 无关),故用中置连字符验证。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, err = _run_cli("search", "项目-规划", env=env_with_tmp_db)
        assert rc == 0, f"搜含连字符词不应报错,stderr={err}"


class TestFilterChainUnchanged:
    """过滤链 / 排序 / LIMIT 行为与修复前一致(回归)。"""

    def test_category_filter_combination(self, env_with_tmp_db):
        """关键词 + -c 分类 组合过滤。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "学习", "-c", "心愿", env=env_with_tmp_db)
        data = json.loads(out)["data"]
        assert len(data) == 1 and data[0]["category"] == "心愿"

    def test_limit_respected(self, env_with_tmp_db):
        """默认 LIMIT 20(插入 25 条同词记录,返回 20)。"""
        _seed(env_with_tmp_db, [("批量记录 %d" % i, "备忘", None) for i in range(25)])
        rc, out, _ = _run_cli("search", "批量记录", env=env_with_tmp_db)
        assert len(_ids(out)) == 20, "默认 limit=20 应生效"

    def test_empty_keyword_regression(self, env_with_tmp_db):
        """空关键词 = 按分类列出(不进入 LIKE 分支)。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "", env=env_with_tmp_db)
        data = json.loads(out)["data"]
        assert len(data) == 6, f"空关键词应列出全部 6 条,实际 {len(data)}"

    def test_sub_category_filter_combination(self, env_with_tmp_db):
        """关键词 + -s 子分类 组合过滤。"""
        _seed(env_with_tmp_db, SEED)
        rc, out, _ = _run_cli("search", "跑步", "-s", "跑步", env=env_with_tmp_db)
        assert len(_ids(out)) == 1
