# -*- coding: utf-8 -*-
"""SM3 穿搭出行域 · 数据层(T4 域文件集,只被 T4 场景使用)

设计依据: `.scratch/v2.0-impl-map/t4-sm3-design.md`(第一性设计笔记)
提供:
  - slot_of(): 槽位判定规则(分类=身份,tag=角色)
  - _clothing_items(): 在家衣物全量(分类路径/标签/照片/访问统计)
  - outfit_payload_v2(): 穿搭推荐(推荐引擎, 3-5 套本地翻页)
  - wardrobe_payload(): 衣橱分析(构成/闲置诚实标注/建议一句)
  - season_payload(): 换季收纳(季节衣物清单 + 收纳位建议)
  - trip_payload_v2(): 出行清单(行程类型规则库 + 健身两层推荐)
  - trip_plan_payload(): 旅行穿搭计划(贪心最少复用/冲突提示/行李汇总)
"""

from datetime import datetime, timedelta

from .tag_ops import get_tags
from .item_ops import _get_photo_base64

SLOTS = ["hat", "inner", "outer", "bottom", "shoes", "acce"]
SLOT_LABELS = {"hat": "帽子", "inner": "内搭", "outer": "外套",
               "bottom": "下装", "shoes": "鞋", "acce": "配饰"}

# 三级分类 → 层角色启发(无「内搭/外套」标签时的兜底)
_OUTER_SUBCATS = {"外套", "卫衣", "毛衣", "夹克", "西装", "风衣",
                  "大衣", "羽绒服", "冲锋衣", "马甲", "开衫"}
_INNER_SUBCATS = {"T恤", "衬衫", "打底", "针织", "背心", "Polo衫",
                  "polo衫", "运动背心", "无袖背心"}

# 温度分层(季节 = 温度派生,不建季节字段): ≥25° 薄 / <15° 厚 / 中间层任意
TEMP_THIN = 25
TEMP_THICK = 15

# 衣橱闲置阈值(天): last_accessed_at 距今超 N 天或从未访问
DORMANT_DAYS = 90

# ── 槽位判定 ─────────────────────────────────────────────

def slot_of(category_path, tags=None):
    """分类=身份,tag=角色 → 槽位 key。

    规则:
      鞋类 → shoes;下装 → bottom
      帽饰配件: tag含帽子 或 三级分类=帽子 → hat;否则 → acce
      上装: tag含外套 → outer;tag含内搭 → inner;
            无层标签 → 三级分类启发(外套系→outer,T恤系→inner,歧义→outer)
      内衣睡衣/袜类/床上用品 → None(不参与拼贴)
    """
    tags = {str(t).strip() for t in (tags or [])}
    path = category_path or ""
    if "鞋类" in path:
        return "shoes"
    if "下装" in path:
        return "bottom"
    if "帽饰配件" in path:
        if "帽子" in tags or path.rstrip("/").endswith("/帽子"):
            return "hat"
        return "acce"
    if "上装" in path:
        if "外套" in tags:
            return "outer"
        if "内搭" in tags:
            return "inner"
        sub = path.rstrip("/").split("/")[-1]
        if sub in _INNER_SUBCATS:
            return "inner"
        return "outer"
    return None


# ── 衣物查询 ─────────────────────────────────────────────

def _clothing_items(conn, status="在家"):
    """全量衣物物品(仅指定状态),附加 tags / photo_base64 / 访问统计。"""
    cursor = conn.cursor()
    cursor.execute("""
        WITH RECURSIVE cat_path AS (
          SELECT id, parent_id, name, name AS full_path, 1 AS lvl
          FROM categories WHERE parent_id IS NULL
          UNION ALL
          SELECT c.id, c.parent_id, c.name,
                 cp.full_path || '/' || c.name, cp.lvl + 1
          FROM categories c JOIN cat_path cp ON c.parent_id = cp.id
        )
        SELECT i.id, i.name, i.category_id, c.name AS category_name,
               cp.full_path, cp.lvl,
               i.access_count, i.last_accessed_at, i.created_at, i.photo
        FROM items i
        JOIN cat_path cp ON i.category_id = cp.id
        LEFT JOIN categories c ON c.id = i.category_id
        WHERE cp.lvl >= 2
          AND (
            cp.full_path LIKE '衣物与穿戴/%'
            OR cp.full_path LIKE '鞋类/%'
          )
          AND i.id IN (
            SELECT item_id FROM item_locations
            WHERE location_status = ? AND quantity > 0
          )
        ORDER BY i.name
    """, (status,))
    rows = cursor.fetchall()
    items = []
    for r in rows:
        photo_b64 = _get_photo_base64(r["photo"]) if r["photo"] else None
        items.append({
            "id": r["id"],
            "name": r["name"],
            "category_id": r["category_id"],
            "category_name": r["category_name"] or "(未分类)",
            "full_path": r["full_path"],
            "tags": get_tags(conn, r["id"]),
            "photo": r["photo"],
            "photo_base64": photo_b64,
            "access_count": r["access_count"] or 0,
            "last_accessed_at": r["last_accessed_at"],
            "created_at": r["created_at"],
        })
    return items


def _ts_epoch(when_str):
    """ISO 时间串 → epoch(解析失败返回 0)。"""
    if not when_str:
        return 0
    try:
        return datetime.fromisoformat(when_str.replace("T", " ")).timestamp()
    except Exception:
        return 0


def _sort_key(it):
    """隐式偏好(升序,直接用 sort 不用 reverse):
    有采纳历史(最后访问)的恒在前,组内按最近优先;
    无历史的按创建时间(新衣优先),再按 id。"""
    if it.get("last_accessed_at"):
        return (0, -_ts_epoch(it["last_accessed_at"]), it["id"])
    return (1, -_ts_epoch(it["created_at"]), it["id"])


def _temp_layer(temperature):
    """温度 → 季节层: '薄' / '厚' / None(中间层)。"""
    if temperature is None:
        return None
    if temperature >= TEMP_THIN:
        return "薄"
    if temperature < TEMP_THICK:
        return "厚"
    return None


def _season_tags(layer):
    return {"薄": {"夏季", "夏", "薄"}, "厚": {"冬季", "冬", "厚"}}.get(layer)


def _fits_layer(it, layer):
    """季节标签过滤: 薄层排除冬季标签, 厚层排除夏季标签, 无层全过。"""
    if layer is None:
        return True
    tags = set(it["tags"])
    if layer == "薄":
        return not (tags & {"冬季", "冬", "厚"})
    return not (tags & {"夏季", "夏", "薄"})


def _style_of(it, occasion):
    """风格标签: 场合标签(tags 含 上班/通勤/运动/约会/正式/家居)优先,否则场合参数,否则日常。"""
    occ_tags = {"上班", "通勤", "约会", "运动", "正式", "家居", "休闲"}
    hit = sorted(set(it["tags"]) & occ_tags)
    if hit:
        return hit[0]
    if occasion:
        return occasion
    return "日常"


# ── 穿搭推荐(SM3-1) ─────────────────────────────────────

def outfit_payload_v2(conn, temperature=None, occasion="", limit=5):
    """推荐引擎: 排除法 + 隐式偏好 + 温度派生 + 成套联动 → limit 套。

    返回结构(拼贴卡模板直接消费):
      {
        summary: {title, subtitle, metrics[]},
        weather: {temperature, occasion, temp_layer},
        sets: [{style, reason, slots: {hat|inner|outer|bottom|shoes|acce: item}},
               ...],
        gap: [槽位缺失名...],
        total: 可选衣物件数,
      }
    item: {id, name, category_name, tags, photo_base64, has_photo}
    """
    items = _clothing_items(conn)
    layer = _temp_layer(temperature)

    slots = {k: [] for k in SLOTS}
    for it in items:
        if not _fits_layer(it, layer):
            continue
        s = slot_of(it["full_path"], it["tags"])
        if s:
            slots[s].append(it)
    for k in slots:
        slots[k].sort(key=_sort_key)

    # 成套联动: tag「成套:xxx」共享组 → 同组物品永远一起出现
    suit_groups = {}
    for k in SLOTS:
        for it in slots[k]:
            for t in it["tags"]:
                if "成套" in t:
                    suit_groups.setdefault(t, []).append((k, it))

    sets = []
    total_avail = sum(len(v) for v in slots.values())
    for i in range(max(1, min(limit, 5))):
        combo = {}
        used_ids = set()
        for k in SLOTS:
            pool = slots[k]
            if not pool:
                continue
            pick = pool[i % len(pool)]
            # 成套: 若选中件带成套标签, 把同组其余件并入对应槽位
            combo[k] = pick
            used_ids.add(pick["id"])
            for t in pick["tags"]:
                if "成套" in t and t in suit_groups:
                    for (gk, gitem) in suit_groups[t]:
                        if gitem["id"] not in used_ids and (gk not in combo):
                            combo[gk] = gitem
                            used_ids.add(gitem["id"])
        if not combo:
            break
        hero = combo.get("outer") or combo.get("inner") or combo.get("bottom")
        style = _style_of(hero, occasion) if hero else (occasion or "日常")
        reason = f"{style} ← {temperature}°C" if temperature is not None else f"{style} · 今日"
        if occasion:
            reason += f" · {occasion}"
        sets.append({"style": style, "reason": reason, "slots": combo})

    gap = [SLOT_LABELS[k] for k in SLOTS if not slots[k]]
    return {
        "summary": {
            "title": "今日穿搭推荐",
            "subtitle": "相册拼贴 · 点击任意照片看原图",
            "metrics": [
                {"label": "可选衣物", "value": f"{total_avail} 件"},
                {"label": "组合", "value": f"{len(sets)} 套"},
                {"label": "温度", "value": f"{temperature}°C" if temperature is not None else "未知"},
                {"label": "场合", "value": occasion or "未指定"},
            ],
        },
        "weather": {"temperature": temperature, "occasion": occasion,
                    "temp_layer": layer},
        "sets": sets,
        "gap": gap,
        "total": total_avail,
    }


# ── 衣橱分析(SM3-2) ─────────────────────────────────────

def wardrobe_payload(conn, dormant_days=DORMANT_DAYS):
    """衣橱结构诊断: 分类构成 + 闲置清单(诚实标注估算) + 建议一句。"""
    items = _clothing_items(conn)
    now = datetime.now()

    dist = {k: 0 for k in SLOTS}
    slot_items = {k: [] for k in SLOTS}
    for it in items:
        s = slot_of(it["full_path"], it["tags"])
        if s:
            dist[s] += 1
            slot_items[s].append(it)

    def _days_since(when_str):
        if not when_str:
            return None
        try:
            return (now - datetime.fromisoformat(when_str.replace("T", " "))).days
        except Exception:
            return None

    dormant = []
    for s in SLOTS:
        for it in slot_items[s]:
            last_days = _days_since(it["last_accessed_at"])
            if it["access_count"] == 0 or (last_days is not None and last_days > dormant_days):
                estimated = it["last_accessed_at"] is None
                when = it["last_accessed_at"] or it["created_at"]
                when_days = _days_since(when)
                dormant.append({
                    "id": it["id"], "name": it["name"],
                    "category_name": it["category_name"], "slot": SLOT_LABELS[s],
                    "tags": it["tags"], "photo_base64": it["photo_base64"],
                    "last_used": when or "从未", "days_idle": when_days,
                    "estimated": estimated,
                })
    dormant.sort(key=lambda x: x["days_idle"] if x["days_idle"] is not None else 10 ** 9)

    total = sum(dist.values())
    dist_data = [{"key": k, "label": SLOT_LABELS[k], "count": dist[k],
                  "pct": round(dist[k] * 100 / total, 1) if total else 0}
                 for k in SLOTS if dist[k] > 0]

    advice = _wardrobe_advice(dist, len(dormant), total, items)
    return {
        "summary": {
            "title": "衣橱闲置分析",
            "subtitle": "结构诊断 · 断舍离建议(参考性)",
            "metrics": [
                {"label": "在家衣物", "value": f"{total} 件"},
                {"label": "闲置", "value": f"{len(dormant)} 件"},
                {"label": "闲置占比", "value": f"{round(len(dormant) * 100 / total, 1)}%" if total else "0%"},
            ],
        },
        "distribution": dist_data,
        "dormant": dormant,
        "advice": advice,
    }


def _wardrobe_advice(dist, dormant_cnt, total, items):
    if total == 0:
        return "衣橱还是空的——先录入几件衣物,再来分析(录物品/拍物品)。"
    parts = []
    top = dist["outer"] + dist["inner"]
    bottom = dist["bottom"]
    if bottom and top > bottom * 2:
        parts.append("上装偏多,下装偏少,可考虑补充下装")
    if bottom and top > 0 and bottom > top * 2:
        parts.append("下装偏多,上装偏少,可考虑补充上装")
    if dormant_cnt and dormant_cnt / total >= 0.3:
        parts.append(f"{dormant_cnt} 件衣物长期未用,可考虑断舍离")
    if not dist.get("shoes"):
        parts.append("鞋类为空,出行搭配缺一环")
    if not dist.get("outer") and not dist.get("inner"):
        parts.append("上装为空,先录入上衣")
    return "、".join(parts) + "。" if parts else "衣橱结构均衡,继续保持。"


# ── 换季收纳(SM3-3) ─────────────────────────────────────

SEASON_ALIAS = {"夏季": {"夏季", "夏", "夏天", "薄"}, "冬季": {"冬季", "冬", "冬天", "厚"},
                "春秋": {"春秋", "春秋季", "过渡季"}}


def _season_match(tags, season):
    keys = SEASON_ALIAS.get(season, {season})
    return bool(set(tags) & keys)


def season_payload(conn, season="夏季", action="收纳"):
    """季节衣物清单(在家),收纳目标位建议;旅游中等异常状态不参与。"""
    items = _clothing_items(conn)
    matched = [it for it in items if _season_match(it["tags"], season)]
    for it in matched:
        it["has_photo"] = bool(it["photo_base64"])

    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT location FROM item_locations
        WHERE location LIKE '%收纳%' OR location LIKE '%箱%' OR location LIKE '%袋%'
        ORDER BY location
    """)
    storage_places = [r["location"] for r in cursor.fetchall()]

    return {
        "summary": {
            "title": f"换季收纳 · {season}",
            "subtitle": "批量勾选后复制回执发给 AI 执行(收纳=移位置+标已收纳)",
            "metrics": [
                {"label": "季节衣物", "value": f"{len(matched)} 件"},
                {"label": "操作", "value": action},
            ],
        },
        "season": season,
        "action": action,
        "items": matched,
        "storage_places": storage_places,
    }


# ── 出行清单(SM3-4) ─────────────────────────────────────

TRIP_RULES = {
    "出差": lambda d: [
        {"name": "洗漱包", "reason": "出差必备"},
        {"name": "换洗衣物", "reason": f"{d} 天的换洗"},
        {"name": "证件(身份证/工卡)", "reason": "出行必带"},
        {"name": "充电器", "reason": "电子设备续航"},
        {"name": "电脑", "reason": "出差办公"},
    ],
    "旅行": lambda d: [
        {"name": "洗漱包", "reason": "旅行必备"},
        {"name": "换洗衣物", "reason": f"{d} 天衣物, 建议 {min(d + 1, 8)} 套"},
        {"name": "证件", "reason": "出行必带"},
        {"name": "充电器", "reason": "电子设备续航"},
        {"name": "旅行收纳袋", "reason": "分装衣物"},
    ],
    "超市": lambda d: [
        {"name": "购物袋", "reason": "装采购物品"},
        {"name": "手机/钱包", "reason": "支付"},
    ],
    "游泳": lambda d: [
        {"name": "泳衣", "reason": "游泳必备"},
        {"name": "泳镜", "reason": "保护眼睛"},
        {"name": "泳帽", "reason": "场馆要求"},
        {"name": "毛巾", "reason": "出水擦干"},
        {"name": "防水袋", "reason": "装湿衣物"},
    ],
    "爬山": lambda d: [
        {"name": "登山鞋", "reason": "防滑护踝"},
        {"name": "水壶", "reason": "补水"},
        {"name": "防晒", "reason": "户外防晒"},
        {"name": "帽子", "reason": "遮阳"},
        {"name": "登山杖", "reason": "省力护膝"},
    ],
    "滑雪": lambda d: [
        {"name": "手套", "reason": "防寒防磨"},
        {"name": "护目镜", "reason": "防雪盲"},
        {"name": "保暖衣物", "reason": "雪场低温"},
        {"name": "护具", "reason": "防摔伤"},
    ],
}

# 护具知识表(健身联动第二层 · 动作 → 护具,可扩展)
GUARD_RULES = [
    {"keywords": ("拉", "划", "引体"), "guard": "拉力手套", "reason": "拉力动作防滑防磨"},
    {"keywords": ("深蹲", "硬拉", "腿"), "guard": "深蹲腰带", "reason": "练腿保护腰部"},
    {"keywords": ("卧推", "推举", "大重量"), "guard": "手肘绷带", "reason": "大重量护肘"},
    {"keywords": (), "guard": "健身手套", "reason": "通用防滑保护"},
]

GYM_BASE = {
    "力量": [{"name": "健身包", "reason": "装训练装备"},
             {"name": "水壶", "reason": "训练补水"},
             {"name": "毛巾", "reason": "擦汗"}],
    "有氧": [{"name": "健身包", "reason": "装训练装备"},
             {"name": "水壶", "reason": "训练补水"},
             {"name": "毛巾", "reason": "擦汗"},
             {"name": "跑步鞋", "reason": "有氧首选"}],
    "休息日": [{"name": "健身包", "reason": "轻量健身包(休息日)"}],
}


# 规则物品名 → 库内匹配关键词(可扩展同义词)
TRIP_SYNONYMS = {
    "跑步鞋": ("跑步鞋", "运动鞋", "跑鞋"),
    "登山鞋": ("登山鞋", "户外鞋"),
    "帽子": ("帽子", "棒球帽", "渔夫帽"),
    "手套": ("手套",),
    "水壶": ("水壶", "水杯", "运动水壶"),
    "毛巾": ("毛巾",),
}


def _match_db_item(items, name_keywords):
    """按名称/标签在库内匹配(在家),返回 item 或 None。"""
    for it in items:
        hay = (it["name"] or "") + " " + " ".join(it["tags"])
        for kw in name_keywords:
            if kw in hay:
                return it
    return None


def trip_payload_v2(conn, trip_type="出差", days=3, plan_type=None, exercises=None,
                    mode="pack"):
    """出行清单: 行程规则库 + 健身两层推荐;库内物品带照片,未录入 → 引导录入。"""
    items = _clothing_items(conn)
    plan = []

    if trip_type == "健身":
        base = GYM_BASE.get(plan_type, GYM_BASE["力量"]) if plan_type else GYM_BASE["力量"]
        for b in base:
            plan.append({"name": b["name"], "reason": b["reason"], "source": "基础物品"})
        guards = []
        for ex in (exercises or []):
            for rule in GUARD_RULES:
                if rule["keywords"] and any(k in ex for k in rule["keywords"]):
                    if rule["guard"] not in guards:
                        guards.append(rule["guard"])
                        break
        if not guards and exercises:
            guards.append(GUARD_RULES[-1]["guard"])
        elif not guards:
            guards.append(GUARD_RULES[-1]["guard"])
        for g in guards:
            plan.append({"name": g, "reason": "护具(动作匹配)", "source": "护具表"})
    elif trip_type in TRIP_RULES:
        for r in TRIP_RULES[trip_type](days):
            plan.append({"name": r["name"], "reason": r["reason"], "source": "行程规则"})
    else:
        plan.append({"name": "自定义物品", "reason": "手动添加", "source": "自定义"})

    result_items = []
    for p in plan:
        kws = TRIP_SYNONYMS.get(p["name"], (p["name"],))
        it = _match_db_item(items, kws)
        if it:
            result_items.append({
                "id": it["id"], "name": it["name"],
                "category_name": it["category_name"], "tags": it["tags"],
                "photo_base64": it["photo_base64"], "has_photo": bool(it["photo_base64"]),
                "reason": p["reason"], "source": p["source"],
                "location_status": "在家", "registered": True,
            })
        else:
            result_items.append({
                "id": None, "name": p["name"], "category_name": "",
                "tags": [], "photo_base64": None, "has_photo": False,
                "reason": p["reason"], "source": p["source"],
                "location_status": "", "registered": False,
            })

    return {
        "summary": {
            "title": "出行带物清单",
            "subtitle": "勾选装箱 → 复制回执发给 AI 标'旅游中';未录入物品引导录入/购物",
            "metrics": [
                {"label": "行程", "value": trip_type},
                {"label": "天数", "value": f"{days} 天"},
                {"label": "清单", "value": f"{len(result_items)} 项"},
            ],
        },
        "trip_type": trip_type,
        "days": days,
        "plan_type": plan_type,
        "mode": mode,
        "items": result_items,
        "unregistered": [x["name"] for x in result_items if not x["registered"]],
    }


# ── 旅行穿搭计划(SM3-5) ─────────────────────────────────

def trip_plan_payload(conn, days=5, temps=None, destination=""):
    """按天分配穿搭: 贪心最少复用 + 冲突提示 + 行李汇总(去重)。"""
    items = _clothing_items(conn)
    slots = {k: [] for k in SLOTS}
    for it in items:
        s = slot_of(it["full_path"], it["tags"])
        if s:
            slots[s].append(it)

    temps = temps or [None] * days
    used = {}                             # item_id → 已用次数
    day_plans = []
    for d in range(days):
        combo = {}
        for k in SLOTS:
            pool = slots[k]
            if not pool:
                continue
            pool_sorted = sorted(pool, key=lambda x: (used.get(x["id"], 0), _sort_key(x), x["id"]))
            pick = pool_sorted[0]
            used[pick["id"]] = used.get(pick["id"], 0) + 1
            combo[k] = pick
        day_plans.append({"day": d + 1, "temp": temps[d], "slots": combo})

    conflicts = []
    for k in SLOTS:
        have = len(slots[k])
        if 0 < have < days:
            conflicts.append({"slot": SLOT_LABELS[k], "have": have, "need": days,
                              "hint": f"{days} 天 {have} 件{SLOT_LABELS[k]}, 部分天数需重复穿"})

    luggage_ids = set()
    for dp in day_plans:
        for it in dp["slots"].values():
            luggage_ids.add(it["id"])
    luggage = []
    for it in items:
        if it["id"] in luggage_ids:
            luggage.append(it)

    return {
        "summary": {
            "title": "旅行穿搭计划",
            "subtitle": f"{destination or '目的地'} · {days} 天 · 每日组合(拼贴卡)",
            "metrics": [
                {"label": "天数", "value": f"{days} 天"},
                {"label": "涉及衣物", "value": f"{len(luggage)} 件"},
                {"label": "冲突", "value": f"{len(conflicts)} 项"},
            ],
        },
        "destination": destination,
        "days": days,
        "day_plans": day_plans,
        "luggage": luggage,
        "conflicts": conflicts,
    }
