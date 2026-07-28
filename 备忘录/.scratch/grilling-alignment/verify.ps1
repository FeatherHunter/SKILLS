# 备忘录 Skill · 验收脚本(v1.1.5 完整版)
# A.4 范式: .scratch/<feature>/verify.ps1
# 创建: 2026-07-28 · Grilling R3 占位 · v1.1.5 ticket 01 完整化
#
# 运行: pwsh .scratch/grilling-alignment/verify.ps1  (或 powershell -File ...)
# 退出码: 0 = 全过 / 1 = 任一项失败

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

# 跳到 skill 根(script 在 .scratch/grilling-alignment/,往上 2 级)
$skillDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location "$skillDir"

$failed = 0

function Write-Check($name, $ok, $detail="") {
    if ($ok) {
        Write-Host "[OK] $name" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $name $detail" -ForegroundColor Red
        $script:failed = 1
    }
}

Write-Host "=== 备忘录 Skill · v1.1.5 验收脚本 ===" -ForegroundColor Cyan
Write-Host ""

# ===== 检查 1: git status 工作区干净(测试副产物被 hook 还原) =====
Write-Host "—— 检查 1: git status 工作区 ——"
# git -C 仓库根跑(skill 根不是 git 根),脚本在 备忘录/ 内,git 路径用 备忘录/
$repoRoot = Split-Path -Parent $skillDir
$gs = git -C "$repoRoot" status --short 备忘录/ 2>&1 | Out-String
# 允许 备忘录.html 漂移(pre-commit hook 还原后应干净;此处检 working tree 须无 .py / .md / .yaml / .html template 改动)
$dirtyFiles = $gs -split "`n" | Where-Object { $_ -match "^\s*[M?]\s+备忘录/(?!备忘录\.html)" }
if ($dirtyFiles.Count -eq 0) {
    Write-Check "git status 工作区干净(允许 备忘录.html 漂移)" $true
} else {
    Write-Check "git status 工作区干净" $false "残留: $($dirtyFiles -join ', ')"
}

# ===== 检查 2: pytest 全过(基线 185 + 1 xfail) =====
Write-Host ""
Write-Host "—— 检查 2: pytest 全过 ——"
$pytestLines = python -m pytest --tb=short -q 2>&1
$pytestExit = $LASTEXITCODE
$pytestOut = $pytestLines -join "`n"
if ($pytestExit -eq 0) {
    # 提取 passed 数(最后一行通常是 "186 passed, 1 warning in 17.58s")
    if ($pytestOut -match "(\d+) passed") {
        $passed = [int]$Matches[1]
        Write-Check "pytest 全过($passed passed · 基线 185)" ($passed -ge 185) "实际 $passed < 185"
    } else {
        Write-Check "pytest 全过" $false "无法解析 passed 数"
    }
} else {
    Write-Check "pytest 全过" $false "exit=$pytestExit"
    Write-Host $pytestOut -ForegroundColor Yellow
}

# ===== 检查 3: CLI smoke(memo_cli help 落 HTML) =====
Write-Host ""
Write-Host "—— 检查 3: CLI smoke(memo_cli help) ——"
$helpOut = python script/memo_cli.py help 2>&1 | Out-String
if ($LASTEXITCODE -eq 0 -and $helpOut -match '"status":\s*"ok"') {
    $skillRootHtml = Join-Path $skillDir "备忘录.html"
    if (Test-Path $skillRootHtml) {
        Write-Check "memo_cli help 生成 HTML + 覆盖 skill 根" $true
    } else {
        Write-Check "memo_cli help 生成 HTML" $false "skill 根 备忘录.html 不存在"
    }
} else {
    Write-Check "memo_cli help 可执行" $false "exit=$LASTEXITCODE"
    Write-Host $helpOut -ForegroundColor Yellow
}

# ===== 检查 4: 结构体检(test_skill_structure.py 全过) =====
Write-Host ""
Write-Host "—— 检查 4: 结构体检(test_skill_structure.py) ——"
$structOut = python -m pytest tests/test_skill_structure.py -v --tb=short 2>&1 | Out-String
if ($LASTEXITCODE -eq 0 -and $structOut -match "(\d+) passed") {
    $structPassed = [int]$Matches[1]
    Write-Check "结构体检全过($structPassed 用例)" $true
} else {
    Write-Check "结构体检全过" $false "exit=$LASTEXITCODE"
    Write-Host $structOut -ForegroundColor Yellow
}

# ===== 检查 5: .githooks 路由(pre-commit 还原 备忘录.html) =====
Write-Host ""
Write-Host "—— 检查 5: .githooks 路由 ——"
$preCommit = Join-Path (Split-Path -Parent $skillDir) ".githooks/pre-commit"
$commitMsg = Join-Path (Split-Path -Parent $skillDir) ".githooks/commit-msg"
$hook1Ok = Test-Path $preCommit
$hook2Ok = Test-Path $commitMsg
Write-Check ".githooks/pre-commit 存在(pytest + 还原 备忘录.html)" $hook1Ok
Write-Check ".githooks/commit-msg 存在(全中文 + Tested-By 守护)" $hook2Ok

# ===== 检查 6(赠): 4 状态 fallback 守护 =====
Write-Host ""
Write-Host "—— 检查 6(赠): 4 状态 fallback 守护 ——"
$fourState = python -m pytest tests/test_4_state_fallback.py -v --tb=short 2>&1 | Out-String
if ($LASTEXITCODE -eq 0 -and $fourState -match "(\d+) passed") {
    $fsPassed = [int]$Matches[1]
    Write-Check "4 状态 fallback 守护($fsPassed 用例)" $true
} else {
    Write-Check "4 状态 fallback 守护" $false
    Write-Host $fourState -ForegroundColor Yellow
}

Pop-Location

Write-Host ""
if ($failed -eq 0) {
    Write-Host "=== 全过 ✅ ===" -ForegroundColor Green
} else {
    Write-Host "=== 有失败项 ❌ ===" -ForegroundColor Red
}
exit $failed
