# SKILL 开发总纲 V1.0 · 自洽校验脚本
# 对应 spec Testing Decisions 的 5 个校验模块
# 用法: powershell -ExecutionPolicy Bypass -File verify.ps1
# 退出码 0 = 全 PASS, 非 0 = 有 FAIL
#
# 关键设计: 全部用字节级字面比较(Encoding.GetByteCount),绕开
# PowerShell 5.1 Select-String 对中文的正则解析 bug。

$ErrorActionPreference = 'Continue'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repo = Split-Path -Parent (Split-Path -Parent $scriptDir)
$totalPass = 0
$totalFail = 0

function Check($name, $condition) {
    if ($condition) {
        Write-Output "  PASS: $name"
        $script:totalPass = $script:totalPass + 1
    } else {
        Write-Output "  FAIL: $name"
        $script:totalFail = $script:totalFail + 1
    }
}

# 字节级字面匹配: 把 needle 和 haystack 都转成 bytes 然后 bstrstr
function ContainsLiteral($file, $needle) {
    $p = Join-Path $script:repo $file
    if (-not (Test-Path -LiteralPath $p)) { return 0 }
    $enc = [System.Text.Encoding]::UTF8
    $haystackBytes = $enc.GetBytes((Get-Content -LiteralPath $p -Raw -Encoding UTF8))
    $needleBytes = $enc.GetBytes($needle)
    if ($needleBytes.Length -eq 0) { return 0 }
    if ($needleBytes.Length -gt $haystackBytes.Length) { return 0 }
    $hits = 0
    for ($i = 0; $i -le $haystackBytes.Length - $needleBytes.Length; $i++) {
        $match = $true
        for ($j = 0; $j -lt $needleBytes.Length; $j++) {
            if ($haystackBytes[$i + $j] -ne $needleBytes[$j]) { $match = $false; break }
        }
        if ($match) { $hits++ }
    }
    return $hits
}

# 计数 = 命中次数
function CountHits($file, $needle) {
    return (ContainsLiteral $file $needle)
}

$mdFiles = @('01-第一性原理.md','02-5层骨架.md','03-触发词设计v2.md','04-可视化与注入v2.md','05-工程仪式.md','06-附录.md','07-HELP与场景完备性.md','README.md','SKILL.md')

Write-Output "=== Module 1: Count checks ==="
Check "README has 7 hooks" ((CountHits 'README.md' '7 个不可违背的钩子') -ge 1)
Check "SKILL.md has 7 hooks" ((CountHits 'SKILL.md' '7 个不可违背的钩子') -ge 1)
Check "HTML has 7 hooks" ((CountHits 'SKILL开发总纲V1.0.html' '7 个不可违背的钩子') -ge 1)
Check "s04 has 13 principles" ((CountHits '04-可视化与注入v2.md' '13 原则') -ge 1)
Check "HTML has 13 principles" ((CountHits 'SKILL开发总纲V1.0.html' '13 原则') -ge 1)
$htmlContent = Get-Content -LiteralPath (Join-Path $repo 'SKILL开发总纲V1.0.html') -Raw -Encoding UTF8
$principleRows = ([regex]::Matches($htmlContent, '<tr><td>(\d+)</td>')).Count
Check "HTML table has 13 rows" ($principleRows -eq 13)
Check "s06 no 4 fail mode title" ((CountHits '06-附录.md' '4 个常见 fail mode') -eq 0)

Write-Output ""
Write-Output "=== Module 2: Non-existence checks ==="
$found68 = $false
foreach ($f in $mdFiles) { if ((CountHits $f '6/8 通过') -gt 0) { $found68 = $true } }
Check "no 6/8 in md files" (-not $found68)
$foundScale = $false
foreach ($f in $mdFiles) { if ((CountHits $f '规模伸缩') -gt 0) { $foundScale = $true } }
foreach ($f in $mdFiles) { if ((CountHits $f '规模自检') -gt 0) { $foundScale = $true } }
foreach ($f in $mdFiles) { if ((CountHits $f '3 层合并') -gt 0) { $foundScale = $true } }
Check "no scale flexibility in md" (-not $foundScale)
Check "s06 no appendix D" ((CountHits '06-附录.md' '附录 D') -eq 0)
Check "s06 no should-not-skillize" ((CountHits '06-附录.md' '何时不该 Skill 化') -eq 0)
Check "s03 no iron-rule-4" ((CountHits '03-触发词设计v2.md' '铁律 4') -eq 0)
Check "s04 no V3 in principle 12" ((CountHits '04-可视化与注入v2.md' '原则 12 · HTML 输出路径约定(V3') -eq 0)
Check "HTML no 6+1" ((CountHits 'SKILL开发总纲V1.0.html' '6+1') -eq 0)
Check "s07 no dead links" ((CountHits '07-HELP与场景完备性.md' 'docs/superpowers') -eq 0)
$archPath = Join-Path $repo '架构图.html'
Check "architecture.html deleted" (-not (Test-Path -LiteralPath $archPath))

Write-Output ""
Write-Output "=== Module 3: Literal correspondence ==="
Check "s04 pseudocode has timeout=30" ((CountHits '04-可视化与注入v2.md' 'timeout=30') -ge 1)
Check "s04 pseudocode has 5MB" ((CountHits '04-可视化与注入v2.md' '5MB') -ge 1)
Check "s04 has secondary validation" ((CountHits '04-可视化与注入v2.md' '二次校验') -ge 1)
Check "s04 principle 10 title" ((CountHits '04-可视化与注入v2.md' '最高优先级') -ge 1)
Check "HTML principle 10 matches md" ((CountHits 'SKILL开发总纲V1.0.html' '最高优先级') -ge 1)
Check "s04 principle 11 complementary" ((CountHits '04-可视化与注入v2.md' '与原则 10 互补') -ge 1)
Check "HTML principle 11 complementary" ((CountHits 'SKILL开发总纲V1.0.html' '与原则 10 互补') -ge 1)
Check "s04 principle 12 no V3" ((CountHits '04-可视化与注入v2.md' '原则 12 · HTML 输出路径约定') -ge 1)
Check "HTML table has principle 12" ((CountHits 'SKILL开发总纲V1.0.html' '<td>12</td>') -ge 1)
Check "s02 full name reference" ((CountHits '02-5层骨架.md' '钩子:Fresh Agent 验证') -ge 1)
Check "s05 full name reference" ((CountHits '05-工程仪式.md' '钩子:Fresh Agent 验证') -ge 1)

Write-Output ""
Write-Output "=== Module 4: Reference closure ==="
Check "s06 appendix C refs s05" ((CountHits '06-附录.md' '通用改造顺序见') -ge 1)
Check "s06 appendix F refs s05" ((CountHits '06-附录.md' '见 [05') -ge 1)
Check "s07 has authority declaration" ((CountHits '07-HELP与场景完备性.md' '本章为 HELP 契约的唯一权威') -ge 1)
Check "s05 SOP step 1 precise" ((CountHits '05-工程仪式.md' '先读 §02 5 层骨架') -ge 1)

Write-Output ""
Write-Output "=== Module 5: New files existence ==="
Check "CONTEXT.md exists" (Test-Path -LiteralPath (Join-Path $repo 'CONTEXT.md'))
Check "CONTEXT.md has scenario constraint" ((CountHits 'CONTEXT.md' '不准删减或重命名') -ge 1)
Check "ADR-0001 exists" (Test-Path -LiteralPath (Join-Path $repo 'docs\adr\0001-a-coordinate-internal-consistency.md'))
Check "ADR-0002 exists" (Test-Path -LiteralPath (Join-Path $repo 'docs\adr\0002-remove-scale-flexibility.md'))
Check "issue-tracker.md exists" (Test-Path -LiteralPath (Join-Path $repo 'docs\agents\issue-tracker.md'))
Check "triage-labels.md exists" (Test-Path -LiteralPath (Join-Path $repo 'docs\agents\triage-labels.md'))
Check "domain.md exists" (Test-Path -LiteralPath (Join-Path $repo 'docs\agents\domain.md'))
Check "AGENTS.md exists" (Test-Path -LiteralPath (Join-Path $repo 'AGENTS.md'))
Check "AGENTS.md has Agent skills block" ((CountHits 'AGENTS.md' '## Agent skills') -ge 1)

Write-Output ""
Write-Output "========================================"
Write-Output "Total: $totalPass PASS / $totalFail FAIL"
Write-Output "========================================"
if ($totalFail -gt 0) { exit 1 } else { exit 0 }