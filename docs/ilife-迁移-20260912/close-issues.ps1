# Close issues for the "development stopped -> moved to ilife" scope (2026-09-12)
#
# Scope: cross-skill / Base components / 5 skills. Every closed issue gets a comment
#        stressing the new project home: https://github.com/FeatherHunter/ilife
#
# Encoding safety: PowerShell 5.1 parses .ps1 as ANSI, so this script stays pure ASCII.
# All CJK text lives in plan.json + the templates, read through .NET with explicit UTF-8.
#
# Usage:
#   .\close-issues.ps1 -DryRun
#   .\close-issues.ps1 -Only 178
#   .\close-issues.ps1
[CmdletBinding()]
param(
  [int[]]$Only,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$utf8 = New-Object System.Text.UTF8Encoding($false)

$root   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # ...\SKILLS
$here   = $PSScriptRoot
$tplDir = Join-Path $here 'comments'

Set-Location $root

$plan = [System.IO.File]::ReadAllText((Join-Path $here 'plan.json'), $utf8) | ConvertFrom-Json

$tplFile = @{
  skill = '01-single-skill.md'
  base  = '02-base-layer.md'
  cross = '03-cross-skill.md'
}

$dropCandidates = @('ready-for-agent', 'ready-for-human', 'needs-triage', 'needs-info')

$tplCache = @{}
function Get-Template([string]$key) {
  if (-not $tplCache.ContainsKey($key)) {
    $p = Join-Path $tplDir $tplFile[$key]
    $tplCache[$key] = [System.IO.File]::ReadAllText($p, $utf8)
  }
  return $tplCache[$key]
}

$items = if ($Only) { $plan | Where-Object { $Only -contains $_.n } } else { $plan }
Write-Host ("Planned: {0} issue(s){1}" -f $items.Count, $(if ($DryRun) { ' [DRY RUN]' } else { '' }))
Write-Host ''

$ok = 0; $fail = 0; $skip = 0; $log = @()

foreach ($it in $items) {
  $n = $it.n
  $tag = "#$n"
  try {
    $view = gh issue view $n --json number,title,state,labels | ConvertFrom-Json
    if ($view.state -ne 'OPEN') {
      $skip++
      Write-Host ("SKIP {0} already {1}" -f $tag, $view.state)
      $log += [pscustomobject]@{ n = $n; result = 'skipped-' + $view.state; title = $view.title }
      continue
    }

    $body = (Get-Template $it.t).Replace('{{SKILL}}', $it.s)
    $tmp  = Join-Path $env:TEMP "ilife-close-$n.md"
    [System.IO.File]::WriteAllText($tmp, $body, $utf8)

    # self-check: read back and compare byte-for-byte content
    if ([System.IO.File]::ReadAllText($tmp, $utf8) -ne $body) { throw 'temp file encoding self-check failed' }
    if ($body -notmatch 'FeatherHunter/ilife') { throw 'body is missing the ilife URL' }

    if ($DryRun) {
      Write-Host ("DRY  {0}  {1}" -f $tag, $view.title)
      Write-Host ("     tpl={0} skill={1} chars={2}" -f $it.t, $it.s, $body.Length)
      continue
    }

    gh issue comment $n --body-file $tmp | Out-Null
    gh issue close $n --reason 'not planned' | Out-Null

    $cur  = @($view.labels | ForEach-Object { $_.name })
    $drop = @($dropCandidates | Where-Object { $cur -contains $_ })
    if ($drop.Count -gt 0) { gh issue edit $n --remove-label ($drop -join ',') | Out-Null }
    if ($cur -notcontains 'wontfix') { gh issue edit $n --add-label 'wontfix' | Out-Null }

    $ok++
    Write-Host ("OK   {0}  {1}" -f $tag, $view.title)
    $log += [pscustomobject]@{ n = $n; result = 'closed'; title = $view.title }
  }
  catch {
    $fail++
    Write-Host ("FAIL {0}  {1}" -f $tag, $_.Exception.Message)
    $log += [pscustomobject]@{ n = $n; result = 'FAILED: ' + $_.Exception.Message; title = '' }
  }
}

Write-Host ''
Write-Host ("Done: closed={0} failed={1} skipped={2}" -f $ok, $fail, $skip)

if (-not $DryRun) {
  $logPath = Join-Path $here 'close-log.csv'
  $log | Export-Csv -Path $logPath -NoTypeInformation -Encoding UTF8
  Write-Host ("Log: {0}" -f $logPath)
}
