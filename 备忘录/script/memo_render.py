#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "memo_query.html"
OUTPUT_DIR = SKILL_DIR / "output"


def render_query(payload, name="memo_query"):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    safe_payload = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    injected = template.replace("<body>", f"<body>\n<script>window.__DATA__ = {safe_payload};</script>", 1)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"{name}_{ts}.html"
    out_path.write_text(injected, encoding="utf-8")
    return str(out_path)


def main():
    payload = json.load(sys.stdin)
    path = render_query(payload)
    print(json.dumps({"status": "ok", "data": {"path": path}, "message": "HTML 已生成"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
