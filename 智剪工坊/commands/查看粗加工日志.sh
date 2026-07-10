#!/bin/bash
# 显示所有 stage="2"（粗加工）的 entry
# 用法：bash 查看粗加工日志.sh

set -e
cd "$(dirname "$0")/.."

LATEST=$(ls -t 00_智剪/中间产物/logs/*.jsonl 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
    echo "❌ 无日志"
    exit 1
fi

echo "=== 粗加工（stage=2）entries from $(basename $LATEST) ==="
grep '"stage": "2"' "$LATEST" | python << 'PYEOF'
import sys, json
for line in sys.stdin:
    try:
        obj = json.loads(line)
        t = obj.get('time', '?')[:19]
        print(f'  [{t}] step={obj.get("step")} action={obj.get("action")} decision={obj.get("decision", "")[:50]}')
    except: pass
PYEOF
