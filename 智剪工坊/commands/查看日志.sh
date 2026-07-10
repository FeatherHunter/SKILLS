#!/bin/bash
# 列出当前任务的所有日志 + 统计
# 用法：bash 查看日志.sh

set -e
cd "$(dirname "$0")/.."

LOG_DIR="00_智剪/logs"

if [ ! -d "$LOG_DIR" ]; then
    echo "❌ 日志目录不存在：$LOG_DIR"
    echo "可能原因：1) AI 还没开始任务  2) 路径不对"
    exit 1
fi

echo "=== 日志文件列表（按时间倒序）==="
ls -lt "$LOG_DIR" 2>/dev/null | head -20

LATEST_JSONL=$(ls -t "$LOG_DIR"/*.jsonl 2>/dev/null | head -1)

if [ -z "$LATEST_JSONL" ]; then
    echo ""
    echo "（暂无 JSONL 日志）"
    exit 0
fi

echo ""
echo "=== 最新 JSONL: $(basename $LATEST_JSONL) ==="
echo "  行数: $(wc -l < "$LATEST_JSONL")"

echo ""
echo "=== 按 stage 统计 ==="
LATEST_JSONL_PATH="$LATEST_JSONL" python << 'PYEOF'
import json, collections, os
log_path = os.environ['LATEST_JSONL_PATH']
with open(log_path, encoding='utf-8') as f:
    counter = collections.Counter()
    errors = 0
    for line in f:
        if line.strip():
            try:
                obj = json.loads(line)
                counter[obj.get('stage', '?')] += 1
                if obj.get('error'):
                    errors += 1
            except: pass
print(f'  错误 entry: {errors}')
for stage, count in sorted(counter.items()):
    print(f'  {stage}: {count} entries')
PYEOF

echo ""
echo "=== 最近 5 条决策 ==="
tail -5 "$LATEST_JSONL" | python << 'PYEOF'
import sys, json
for line in sys.stdin:
    if line.strip():
        try:
            obj = json.loads(line)
            t = obj.get('time', '?')[:16]
            print(f'  [{t}] stage={obj.get("stage")} action={obj.get("action")} decision={obj.get("decision", "")[:60]}')
        except: pass
PYEOF
