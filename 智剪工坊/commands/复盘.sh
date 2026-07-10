#!/bin/bash
# 完整复盘：人类可读 .md + 关键 .jsonl 决策
# 用法：bash 复盘.sh

set -e
cd "$(dirname "$0")/.."

LOG_DIR="00_智剪/中间产物/logs"

LATEST_MD=$(ls -t "$LOG_DIR"/*.md 2>/dev/null | head -1)
LATEST_JSONL=$(ls -t "$LOG_DIR"/*.jsonl 2>/dev/null | head -1)

if [ -z "$LATEST_MD" ]; then
    echo "❌ 无 .md 日志"
    exit 1
fi

echo "=== 人类可读 (.md) ==="
cat "$LATEST_MD"

if [ -n "$LATEST_JSONL" ]; then
    echo ""
    echo "=== 关键 JSONL 决策 ==="
    grep '"action": "review"\|"action": "yaml_stage_complete"\|"error"' "$LATEST_JSONL" | python << 'PYEOF'
import sys, json
for line in sys.stdin:
    try:
        obj = json.loads(line)
        t = obj.get('time', '?')[:19]
        err = obj.get('error') or '-'
        print(f'  [{t}] action={obj.get("action")} decision={obj.get("decision", "")[:60]} error={err}')
    except: pass
PYEOF
fi
