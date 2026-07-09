"""lib.stage1_checklist — v1.1 阶段 1 操作清单生成器

把 intent.json 的每一条信息 1:1 映射为可执行操作（6 象限）。
输出 markdown 草稿，作为阶段 2 的执行契约。

用法:
    from stage1_checklist import generate_checklist
    md = generate_checklist(intent_path)
    Path(out_md).write_text(md, encoding="utf-8")
"""
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional


# 输出目录约定（v1.1）
INTERMEDIATE_DIR = "中间产物"
CHECKLIST_MD = "操作清单.md"


def _parse_time(t: Any) -> Optional[float]:
    """复用 executor.py 的时间解析（失败返回 None）。"""
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t)
    s = str(t).strip()
    m = re.match(r'^(\d+):(\d{1,2})(?::(\d{1,2}))?$', s)
    if m:
        if m.group(3):
            return int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))
        return int(m.group(1))*60 + int(m.group(2))
    m = re.match(r'^(\d+)分(?:(\d+)秒)?$', s)
    if m:
        return int(m.group(1))*60 + (int(m.group(2)) if m.group(2) else 0)
    m = re.match(r'^(\d+(?:\.\d+)?)\s*(?:分钟|分|min|m)$', s)
    if m:
        return float(m.group(1))*60
    m = re.match(r'^(\d+(?:\.\d+)?)\s*(?:秒|sec|s)?$', s, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _format_ops_human(ops: Dict, voice: str) -> str:
    """把 ops dict 转大白话描述。"""
    if not ops:
        ops = {}
    parts = []
    if 'trim-head' in ops and ops['trim-head'].get('on'):
        parts.append(f"掐头 {ops['trim-head'].get('sec', '?')}s")
    if 'trim-tail' in ops and ops['trim-tail'].get('on'):
        parts.append(f"去尾 {ops['trim-tail'].get('sec', '?')}s")
    if 'cut-middle' in ops and ops['cut-middle'].get('on'):
        f, t = ops['cut-middle'].get('from', '?'), ops['cut-middle'].get('to', '?')
        parts.append(f"切掉中间 {f}-{t}")
    if 'pin-range' in ops and ops['pin-range'].get('on'):
        f, t = ops['pin-range'].get('from', '?'), ops['pin-range'].get('to', '?')
        parts.append(f"只保留 {f}-{t}")
    if 'speed-up' in ops and ops['speed-up'].get('on'):
        parts.append(f"加速 {ops['speed-up'].get('factor', '?')}x")
    if 'slow-down' in ops and ops['slow-down'].get('on'):
        parts.append(f"减速 {ops['slow-down'].get('factor', '?')}x")

    voice_text = {
        'keep': '',
        'mute': '+ 静音',
        'bgm-only': '+ 仅 BGM',
        'keep-with-filler-removed': '+ 去水词',
    }.get(voice, '')

    if not parts and not voice_text:
        return "啥都不动"
    return ' + '.join(parts) + (voice_text if voice_text else '')


def _has_any_op(ops: Dict) -> bool:
    return bool(ops) and any(
        isinstance(v, dict) and v.get('on') for v in ops.values()
    )


def _detect_fuzzy(intent: Dict) -> List[Dict]:
    """模糊项检测（D 象限）。"""
    fuzzy = []

    for v in intent.get('videos', []):
        if v.get('exclude'):
            continue
        idx = v.get('index')
        notes = (v.get('notes') or '').strip()
        # D1: notes 含模糊动词 / BGM 暗示
        if notes and ('BGM' in notes or '音乐' in notes or 'bgm' in notes.lower()):
            fuzzy.append({
                "id": f"BG{idx}",
                "source": f"videos[{idx}].notes",
                "raw": notes,
                "question": f"视频 #{idx} 提到 BGM/音乐，具体怎么处理？",
                "ai_default": "不假设",
                "must_ask": True,
            })

        # D5: voice=keep-with-filler-removed
        if v.get('voice') == 'keep-with-filler-removed':
            fuzzy.append({
                "id": f"FW{idx}",
                "source": f"videos[{idx}].voice",
                "raw": "keep-with-filler-removed",
                "question": f"视频 #{idx} 标了去水词，走完整 remove_fillers 流程吗？",
                "ai_default": "走默认阈值",
                "must_ask": False,
            })

        # D6: 无 ops 但有 summary
        if not _has_any_op(v.get('ops', {})) and v.get('summary'):
            fuzzy.append({
                "id": f"EM{idx}",
                "source": f"videos[{idx}]",
                "raw": "有 summary 无 ops",
                "question": f"视频 #{idx} ({v.get('summary')}) 啥都不动吗？",
                "ai_default": "keep 整段",
                "must_ask": False,
            })

    # D2: overall_intent 含文字 / 字幕 / 标签 等
    overall = intent.get('project', {}).get('overall_intent', '')
    if overall and ('文字' in overall or '字幕' in overall or '标签' in overall):
        fuzzy.append({
            "id": "TXT",
            "source": "project.overall_intent",
            "raw": overall[:50] + ('...' if len(overall) > 50 else ''),
            "question": "文字卡 / 字幕什么规则（停留时长 / 范围 / 内容来源）？",
            "ai_default": "2s + AI 写 + 全部视频",
            "must_ask": True,
        })

    # D3: overall_intent 含 接图 / 插入图片 / 配图
    if overall and ('接图' in overall or '插入图片' in overall or '配图' in overall or '.jpg' in overall or '.png' in overall):
        fuzzy.append({
            "id": "IMG",
            "source": "project.overall_intent",
            "raw": overall[:50] + ('...' if len(overall) > 50 else ''),
            "question": "图片插入规则（停留时长 / 过渡效果 / 文字说明）？",
            "ai_default": "各 3s + 淡入淡出",
            "must_ask": True,
        })

    # D4: cover.prompt 含 "讨论"
    cover = intent.get('cover', {})
    if cover.get('prompt') and ('讨论' in cover.get('prompt', '') or '我想' in cover.get('prompt', '')):
        fuzzy.append({
            "id": "COV",
            "source": "cover.prompt",
            "raw": cover.get('prompt', '')[:50] + ('...' if len(cover.get('prompt', '')) > 50 else ''),
            "question": "封面 prompt：讨论还是直接生成？",
            "ai_default": "不假设",
            "must_ask": True,
        })

    # D7: 自由素材视频（在 sequence 外的非 exclude 视频）
    seq_video_set = set()
    for seq in intent.get('sequences', []):
        for vi in seq.get('videos', []):
            seq_video_set.add(vi)
    free_videos = [
        v.get('index') for v in intent.get('videos', [])
        if not v.get('exclude') and v.get('index') not in seq_video_set
    ]
    if free_videos:
        fuzzy.append({
            "id": "FREE",
            "source": "intent.json (sequence 推导)",
            "raw": f"自由视频: {free_videos}",
            "question": f"这些自由素材视频 #{free_videos} 在最终成片怎么安排？",
            "ai_default": "集中放结尾（模板 Stage 决定顺序）",
            "must_ask": False,
        })

    return fuzzy


def _collect_f_per_video(intent: Dict) -> List[Dict]:
    """E 象限：per-video 推断标记。"""
    rows = []
    for v in intent.get('videos', []):
        idx = v.get('index')
        notes = (v.get('notes') or '').strip()
        has_op = _has_any_op(v.get('ops', {}))

        if v.get('exclude'):
            mark = "⏭️"
        elif has_op and notes:
            mark = "✅+⚠️"
        elif has_op:
            mark = "✅"
        elif notes:
            mark = "⚠️"
        else:
            mark = "❓"

        rows.append({"index": idx, "mark": mark})
    return rows


def _collect_f_out_of_scope(intent: Dict) -> List[Dict]:
    """F 象限：识别未在 SKILL v1.1 范围内的字段。"""
    KNOWN_TOP_KEYS = {
        "_meta", "project", "output", "sequences", "videos", "cover", "ending"
    }
    out = []
    for k in intent.keys():
        if k not in KNOWN_TOP_KEYS:
            out.append({
                "field": k,
                "reason": "本流程不处理（请 AI 主动询问是否需要支持）",
            })
    return out


def generate_checklist(intent: Dict, workspace: Optional[Path] = None) -> str:
    """生成操作清单 markdown。

    Args:
        intent: 解析后的 intent.json dict
        workspace: workspace 路径（用于显示）

    Returns:
        操作清单 markdown 文本
    """
    project = intent.get('project', {})
    output = intent.get('output', {})
    sequences = intent.get('sequences', [])

    # 统计
    videos = intent.get('videos', [])
    total_v = len(videos)
    excluded_v = sum(1 for v in videos if v.get('exclude'))
    process_v = total_v - excluded_v

    seq_video_set = set()
    for seq in sequences:
        for vi in seq.get('videos', []):
            seq_video_set.add(vi)
    free_videos = [
        v.get('index') for v in videos
        if not v.get('exclude') and v.get('index') not in seq_video_set
    ]
    in_seq_videos = [v.get('index') for v in videos if v.get('index') in seq_video_set and not v.get('exclude')]

    md_lines = []
    md_lines.append("# 操作清单 v1（草稿，待用户确认）")
    md_lines.append("")
    md_lines.append(f"> **状态**：草稿")
    md_lines.append(f"> **生成时间**：{datetime.now().isoformat()}")
    if workspace:
        md_lines.append(f"> **Workspace**：{workspace}")
    md_lines.append(f"> **来源**：intent.json (修订号 v{intent.get('_meta', {}).get('revision', '?')})")
    md_lines.append(f"> **AI 执行契约**：本清单「已确认」后才进入阶段 2 粗加工。")
    md_lines.append("")

    # A. per-video
    md_lines.append("## A. per-video 操作")
    md_lines.append("")
    md_lines.append("| # | 文件 | 处理（人话） | 落地 step | 状态 |")
    md_lines.append("|---|------|-------------|----------|------|")
    for v in videos:
        idx = v.get('index')
        file = v.get('file', '?')
        if v.get('exclude'):
            md_lines.append(f"| {idx} | `{file}` | **跳过** | - | n/a |")
            continue
        ops = v.get('ops', {}) or {}
        voice = v.get('voice', 'keep')
        human = _format_ops_human(ops, voice)
        needs_asr = voice not in ('mute', 'bgm-only')
        step = "2.1 ASR → 2.2 处理" if needs_asr else "2.2 直接处理"
        md_lines.append(f"| {idx} | `{file}` | {human} | {step} | pending |")
    md_lines.append("")
    md_lines.append(f"**统计**：{total_v} 总 / {excluded_v} 跳过 / {process_v} 处理 / {len(in_seq_videos)} sequence 内 / {len(free_videos)} 自由素材")
    md_lines.append("")

    # B. project-level
    md_lines.append("## B. project-level 操作")
    md_lines.append("")
    md_lines.append("| 来源字段 | 拆解后操作（人话） | 落地 | 状态 |")
    md_lines.append("|----------|------------------|------|------|")
    overall = project.get('overall_intent', '')
    if overall:
        md_lines.append(f"| `project.overall_intent` | {overall[:40]}{'...' if len(overall) > 40 else ''} | Step 4 兜底 | pending |")
    target_len = project.get('target_length')
    if target_len:
        md_lines.append(f"| `project.target_length` | 时长预算参考：{target_len} | - | info |")
    aspect = output.get('aspect_ratio')
    if aspect:
        md_lines.append(f"| `output.aspect_ratio` | Step 2.2 pillarbox 到 {aspect} | Step 2.2 | info |")
    cover = intent.get('cover', {})
    if cover.get('type'):
        md_lines.append(f"| `cover.type`={cover['type']} | 用 AI 生成封面 | 阶段 4 收尾 | pending |")
    if cover.get('prompt'):
        md_lines.append(f"| `cover.prompt` | (讨论后生成) | Step 4 | pending |")
    ending = intent.get('ending', {})
    if ending:
        md_lines.append(f"| `ending` | 跳过（空） | - | n/a |")
    md_lines.append("")

    # C. sequence
    md_lines.append("## C. sequence 约束")
    md_lines.append("")
    md_lines.append("| sequence 名 | 包含视频 | 转场配置 | 产物路径 |")
    md_lines.append("|------------|---------|---------|---------|")
    for seq in sequences:
        name = seq.get('name', '?')
        vids = seq.get('videos', [])
        # 转场
        trans = seq.get('transitions', [])
        if trans:
            dur = trans[0].get('duration', 0.5)
            ttype = trans[0].get('type', 'fade')
            trans_str = f"{dur}s {ttype}"
        else:
            trans_str = "无"
        md_lines.append(f"| {name} | {vids} | {trans_str} | `组合/{name}.mp4` |")
    if free_videos:
        md_lines.append("")
        md_lines.append(f"**未约束视频（自由素材）**：`{free_videos}`")
        md_lines.append("→ 不在 Step 3 处理，留给模板工作流 Stage 顺序阶段。")
    md_lines.append("")

    # D. 模糊项
    fuzzy = _detect_fuzzy(intent)
    md_lines.append("## D. 模糊项 / 待澄清（汇总）")
    md_lines.append("")
    md_lines.append("| # | 来源 | 模糊内容 | AI 默认假设 | 是否必须问 |")
    md_lines.append("|---|------|---------|------------|-----------|")
    for f in fuzzy:
        must = "✅ 必须问" if f['must_ask'] else "⚠️ 建议问"
        md_lines.append(f"| {f['id']} | `{f['source']}` | {f['raw'][:40]}... | {f['ai_default']} | {must} |")
    md_lines.append("")

    # E. AI 推断 vs 用户明确
    md_lines.append("## E. AI 推断 vs 用户明确（透明标记）")
    md_lines.append("")
    e_rows = _collect_f_per_video(intent)
    md_lines.append("| 视频 # | 标记 |")
    md_lines.append("|--------|------|")
    for r in e_rows:
        md_lines.append(f"| {r['index']} | {r['mark']} |")
    md_lines.append("")
    md_lines.append("**图例**：")
    md_lines.append("- ✅ = 用户明确（ops 中有 on=true）")
    md_lines.append("- ⚠️ = AI 推断（notes / overall_intent / cover.prompt）")
    md_lines.append("- ❓ = 未提及（无 ops/intent/notes）")
    md_lines.append("- ⏭️ = 跳过（exclude）")
    md_lines.append("")

    # F. 未覆盖字段
    f_out = _collect_f_out_of_scope(intent)
    md_lines.append("## F. 未覆盖字段（out-of-scope）")
    md_lines.append("")
    if f_out:
        md_lines.append("| 字段 | 不处理的原因 |")
        md_lines.append("|------|------------|")
        for f in f_out:
            md_lines.append(f"| `{f['field']}` | {f['reason']} |")
    else:
        md_lines.append("无。intent.json 所有字段都在范围内处理。")
    md_lines.append("")

    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"v1 草稿，{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md_lines.append("")

    return "\n".join(md_lines)


def generate_and_save(intent_path: str, workspace: str, force: bool = False) -> str:
    """便捷函数：读 intent.json → 生成操作清单 → 保存到 workspace/中间产物/操作清单.md。

    Args:
        force: 强制覆盖（即使已有已确认版）

    Returns: 生成的清单路径。如果已有已确认版且非 force，返回原路径。
    """
    intent = json.loads(Path(intent_path).read_text(encoding="utf-8"))
    workspace_p = Path(workspace)
    out_dir = workspace_p / "00_智剪" / "粗加工" / INTERMEDIATE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / CHECKLIST_MD

    # 保护：如果已存在"已确认"版，非 force 时不覆盖
    if not force and out_path.exists():
        existing = out_path.read_text(encoding="utf-8")
        if "已确认" in existing[:200]:
            print(f"  ⚠️ 操作清单已确认版已存在，跳过生成（用 --force 强制覆盖）")
            return str(out_path)

    md = generate_checklist(intent, workspace_p)
    out_path.write_text(md, encoding="utf-8")
    return str(out_path)


# CLI
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="v1.1 阶段 1 操作清单生成器")
    p.add_argument("--intent", required=True, help="intent.json 路径")
    p.add_argument("--workspace", required=True, help="workspace 根目录")
    args = p.parse_args()
    out = generate_and_save(args.intent, args.workspace)
    print(f"✓ 操作清单: {out}")