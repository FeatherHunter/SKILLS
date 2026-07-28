# 备忘录 Skill · 验收脚本(占位)
# A.4 范式要求文件存在,本脚本将在 R5 后完整化
# 创建: 2026-07-28 · Grilling R3

$ErrorActionPreference = "Stop"
$skillDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "=== 备忘录 Skill · Grilling 验收脚本 ==="
Write-Host "占位版本 · R5 后完整化"
Write-Host ""
Write-Host "R1+R2+R3 已完成决策 18 项,落地 5 个 capture 文件:"
Write-Host "  - CONTEXT.md (术语表)"
Write-Host "  - docs/adr/0001-version-sot.md"
Write-Host "  - docs/adr/0002-skill-md-dedup-and-dir-merge.md"
Write-Host "  - docs/adr/0003-b-execution-fallback.md"
Write-Host "  - docs/adr/0004-a-structure-files.md"
Write-Host ""
Write-Host "待办: R4 (D 工程仪式) + R5 (C 架构合规)"
Write-Host ""

# 临时校验: pytest 是否仍能跑通(无回归)
Write-Host "[临时校验] pytest 174 测试通过检查..."
$env:PYTHONUTF8 = "1"
Push-Location "$skillDir"
try {
    $result = python -m pytest tests/ --tb=short -q 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] pytest 全过(基线 174/174)" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] pytest 有失败,请检查" -ForegroundColor Red
        Write-Host $result
        exit 1
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "=== 占位脚本结束 · R5 后扩展 ==="
