"""强制 overwrite prompt(不依赖原文本)"""
import yaml
from pathlib import Path

YAML = Path("/mnt/d/2Study/StudyNotes/SKILLS/居家管家/references/scenarios.yaml")

T = {
    "search_default": ("我要查物品:", [("物品名", "")]),
    "search_by_location": ("我要查这个位置上的物品:", [("位置(客厅/冰箱 等)", "")]),
    "search_by_tag": ("我要按标签查:", [("标签", "")]),
    "search_by_status": ("我要查当前状态是 X 的物品:", [("状态(在家/备用/旅游中等)", "")]),
    "detail_by_id": ("我要看这个物品的详情:", [("ID", "")]),
    "add_text": ("我要录入新物品:", [
        ("物品名", ""), ("位置(客厅/冰箱 等)", ""),
        ("分类(衣物/食品/数码 等)", ""), ("标签(逗号分隔,至少 10 个)", ""),
        ("数量(默认 1)", ""), ("备注", ""),
    ]),
    "add_photo": ("我要按图片录入新物品:", [
        ("图片(附图)", ""), ("物品名", ""),
        ("分类(可由 AI 推测)", ""), ("位置(客厅/冰箱 等)", ""),
        ("标签(从图片识别,至少 10 个)", ""),
    ]),
    "update_generic": ("我要修改物品:", [
        ("物品(名称或 ID)", ""), ("要改的字段", ""), ("新值", ""),
    ]),
    "move_variant": ("我要移动物品:", [
        ("物品(名称或 ID)", ""), ("旧位置", ""), ("新位置", ""),
    ]),
    "plus_variant": ("我要补充物品库存:", [
        ("物品(名称或 ID)", ""), ("数量", ""), ("位置", ""),
    ]),
    "minus_variant": ("我要减少物品:", [
        ("物品(名称或 ID)", ""), ("数量", ""),
    ]),
    "tags_variant": ("我要修改物品标签:", [
        ("物品(名称或 ID)", ""), ("标签操作(覆盖/追加/删除)", ""),
        ("标签值(逗号分隔)", ""),
    ]),
    "status_variant": ("我要更改物品状态:", [
        ("物品(名称或 ID)", ""),
        ("新状态(已废弃/借用中/维修中/快递中/穿着中/在家 等)", ""),
    ]),
    "inventory_location": ("我要盘点这个位置的物品:", [("位置", "")]),
    "inventory_all": ("我要全屋盘点:", []),
    "outfit_pick": ("今天穿什么?(请同时告诉我当地天气,或让 AI 自己获取)", []),
    "travel_pack": ("我要出门,标记这些物品为'旅游中':", [
        ("物品清单(逗号或换行分隔)", ""),
    ]),
    "travel_return": ("我回家了,把旅游中的物品标回'在家':", []),
    "stats_summary": ("我要看家里物品总览:", []),
    "stats_frequent": ("我要看最常用的物品 TOP:", [("数量(默认 20)", "")]),
    "stats_dormant": ("我要看长期没碰的物品:", [("数量(默认 20)", "")]),
    "stats_expiring": ("我要看过期预警:", [
        ("天数窗口(默认 30)", ""),
        ("(可选)只看已过期:true/false", ""),
        ("(可选)分类 ID", ""),
    ]),
    "tag_list": ("我要看所有标签:", []),
    "tag_merge": ("我要合并标签:", [("旧标签", ""), ("新标签", "")]),
    "search_express": ("我要看在途快递:", []),
    "account_list": ("我要看所有账号:", []),
    "account_add": ("我要存账号:", [
        ("平台(淘宝/微信 等)", ""), ("用户名", ""), ("密码", ""),
        ("主密钥(至少 8 字符)", ""),
    ]),
    "account_show": ("我要查看账号密码:", [
        ("平台", ""), ("主密钥", ""),
    ]),
    "lint_health": ("我要做数据健康检查:", []),
    "suggest_location": ("[录物品子流程] 帮我推荐这个分类的常用位置:", [
        ("分类(衣物/食品 等)", ""),
    ]),
    "find_location": ("[录物品子流程] 把新物品放在和这个参考物品相同位置:", [
        ("参考物品名", ""),
    ]),
    "help_center": ("我要看居家管家能做什么:", []),
}


def make_prompt(scenario_id):
    if scenario_id not in T:
        return None
    skeleton, fields = T[scenario_id]
    if not fields:
        return skeleton
    lines = [f"  - {label}: ___" for label, _ in fields]
    return f"{skeleton}\n\n请填入:\n" + "\n".join(lines)


def main():
    data = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    n = 0
    for s in data.get("scenarios", []):
        sid = s.get("scenario_id", "")
        new = make_prompt(sid)
        if new is None:
            print(f"  ⚠ no template for {sid}, skip")
            continue
        s["prompt"] = new
        n += 1
    YAML.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8"
    )
    print(f"✓ {n} prompts 重写为尾部填入形式")


if __name__ == "__main__":
    main()
