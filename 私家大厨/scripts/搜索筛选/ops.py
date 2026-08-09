# ops.py - 私家大厨 · 搜索筛选域(search)数据层
#
# 职责: 检索契约 7 字段查询 / 排除食材(NOT 条件) / 7 类维度筛选 / 错字纠错候选(suggest)
# 隔离契约: 本域只动 scripts/搜索筛选/ + templates/搜索筛选/ + render_搜索筛选 + scenes/搜索筛选.yaml + tests/test_搜索筛选.py
#
# G4 grilling 定案(2026-08-08)+ T7 实施(2026-08-09):
#   1. 检索契约 7 字段 = id/name/difficulty/total_time_minutes/status/avg_rating/tags(T2 数据层已补 LEFT JOIN)
#   2. search-2 错字纠错: 无结果 → suggest(同音/形近,字符 2-gram + difflib)→ AI 或自动纠错「你是不是想找」
#   3. search-6 排除食材: 「不吃/不要/忌 X」→ NOT EXISTS(ingredients/flavors/diet_tags,LIKE)
#   4. search-3~12 维度筛选: 菜系/时间/难度/炊具/口味/季节/状态 + 组合(≤3 维,§07 rule_2)
import os
import sys
import difflib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import query

# 7 字段检索契约(T2 产物 · 与 recipe_manager.search_as_dict 同构,追加筛选/排除能力)
_SEARCH_FIELDS = """
    r.id, r.name, r.difficulty, r.total_time_minutes, r.status,
    ROUND(AVG(rh.rating), 1) AS avg_rating,
    GROUP_CONCAT(DISTINCT tags.tag_name) AS tags
"""

_SEARCH_FROM = """
    FROM recipes r
    LEFT JOIN ingredients i ON r.id = i.recipe_id
    LEFT JOIN recipe_history rh ON r.id = rh.recipe_id
    LEFT JOIN (
        SELECT recipe_id, flavor AS tag_name FROM recipe_flavors
        UNION ALL
        SELECT recipe_id, tag AS tag_name FROM recipe_diet_tags
    ) tags ON r.id = tags.recipe_id
"""

# 维度筛选 → (SQL 片段, 参数值变换)。LIKE 匹配子表列(菜系/炊具/口味/季节均在子表)
_FILTER_SQL = {
    "cuisine":   ("EXISTS (SELECT 1 FROM recipe_categories c WHERE c.recipe_id = r.id AND c.cuisine_type LIKE ?)", "%"),
    "time_max":  ("r.total_time_minutes <= ?", None),
    "difficulty":("r.difficulty = ?", None),
    "status":    ("r.status = ?", None),
    "cookware":  ("EXISTS (SELECT 1 FROM cookware w WHERE w.recipe_id = r.id AND w.name LIKE ?)", "%"),
    "flavor":    ("EXISTS (SELECT 1 FROM recipe_flavors f WHERE f.recipe_id = r.id AND f.flavor LIKE ?)", "%"),
    "season":    ("EXISTS (SELECT 1 FROM recipe_seasons s WHERE s.recipe_id = r.id AND s.season LIKE ?)", "%"),
}

_SORT_SQL = {
    "rating":  "ORDER BY avg_rating IS NULL, avg_rating DESC, r.name",
    "updated": "ORDER BY r.updated_at DESC, r.name",
    "name":    "ORDER BY r.name",
}


def _like(v: str) -> str:
    """LIKE 参数包装(前后通配)"""
    return f"%{v}%"


def _split_multi(v):
    """逗号分隔多值(如 --difficulty 简单,快手菜)"""
    return [x.strip() for x in v.split(",") if x.strip()] if v else []


def search_recipes(keyword: str = "", exclude: list = None, filters: dict = None,
                   sort: str = "rating") -> list:
    """检索契约 7 字段查询(关键词/排除/维度筛选任意组合)

    Args:
        keyword: 菜名/食材关键词(空 = 全部)
        exclude: 排除食材列表(「不吃/不要/忌 X」,NOT EXISTS ingredients/flavors/diet_tags)
        filters: {cuisine/time_max/difficulty/status/cookware/flavor/season: str|list}
        sort: rating(默认,评分降序无历史排后)/ updated / name
    """
    where = ["r.status != '已废弃'"]
    params = []

    kw = (keyword or "").strip()
    if kw:
        where.append("(r.name LIKE ? OR i.name LIKE ?)")
        params.extend((_like(kw), _like(kw)))

    for ex in (exclude or []):
        ex = (ex or "").strip()
        if not ex:
            continue
        where.append(
            "NOT EXISTS (SELECT 1 FROM ingredients x WHERE x.recipe_id = r.id AND x.name LIKE ?)"
        )
        where.append(
            "NOT EXISTS (SELECT 1 FROM recipe_flavors f WHERE f.recipe_id = r.id AND f.flavor LIKE ?)"
        )
        where.append(
            "NOT EXISTS (SELECT 1 FROM recipe_diet_tags d WHERE d.recipe_id = r.id AND d.tag LIKE ?)"
        )
        params.extend((_like(ex), _like(ex), _like(ex)))

    for key, raw in (filters or {}).items():
        if key not in _FILTER_SQL or not raw:
            continue
        sql_tpl, wrap = _FILTER_SQL[key]
        values = _split_multi(str(raw)) if isinstance(raw, str) else [raw]
        if key == "time_max":
            values = [int(values[0])] if values else []
        if not values:
            continue
        if len(values) == 1:
            v = values[0]
            where.append(sql_tpl)
            if key == "time_max":
                params.append(int(v))
            elif wrap == "%":
                params.append(_like(str(v)))
            else:
                params.append(str(v))
        else:
            # 多值(难度/状态): IN (?, ?)
            placeholders = ",".join("?" for _ in values)
            sql = sql_tpl
            if sql_tpl.startswith("r."):
                col = sql_tpl.split(" ", 1)[0]
                where.append(f"{col} IN ({placeholders})")
            else:
                where.append(sql_tpl.replace("LIKE ?", "IN (" + placeholders + ")"))
            params.extend(str(v) for v in values)

    sql = (
        f"SELECT DISTINCT {_SEARCH_FIELDS} {_SEARCH_FROM}"
        f" WHERE {' AND '.join(where)}"
        f" GROUP BY r.id, r.name, r.difficulty, r.total_time_minutes, r.status"
        f" {_SORT_SQL.get(sort, _SORT_SQL['rating'])}"
    )
    rows = query(sql, tuple(params))
    for row in rows:
        row["tags"] = (row.get("tags") or "").split(",") if row.get("tags") else []
    return rows


def list_all_recipes(sort: str = "updated") -> list:
    """查看全部(search-13): 全部未废弃菜,7 字段,默认按更新时间倒序"""
    return search_recipes(keyword="", sort=sort)


# ── 错字纠错候选(search-2)──────────────────────────────────────────────

def _bigrams(s: str) -> set:
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}


def _similarity(a: str, b: str) -> float:
    """字符串相似度(0~1): 取 字符 2-gram Jaccard 与 difflib 序列比对的较大值
    覆盖同音/形近: 宫暴鸡丁 vs 宫保鸡丁 → difflib 0.75;错字替换/漏字 → 2-gram 命中
    """
    if not a or not b:
        return 0.0
    ga, gb = _bigrams(a), _bigrams(b)
    jaccard = len(ga & gb) / len(ga | gb) if (ga | gb) else 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return max(jaccard, ratio)


def suggest(keyword: str, limit: int = 5) -> list:
    """无结果时的纠错候选: 从库内菜名找同音/形近(相似度 ≥ 0.4,降序取 top N)
    search-2 契约: AI 提示「你是不是想找: X」并直接展示正确结果
    """
    kw = (keyword or "").strip()
    if not kw:
        return []
    rows = query("SELECT id, name FROM recipes WHERE status != '已废弃'")
    scored = []
    for r in rows:
        if kw in r["name"] or r["name"] in kw:
            continue  # 直接命中会被 search 匹配,无需纠错
        score = _similarity(kw, r["name"])
        if score >= 0.4:
            scored.append({"name": r["name"], "id": r["id"], "score": round(score, 3)})
    scored.sort(key=lambda s: (-s["score"], s["name"]))
    return scored[:limit]
