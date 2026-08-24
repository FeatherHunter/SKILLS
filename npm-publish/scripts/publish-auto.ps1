param(
  [Parameter(Mandatory=$true)][string]$PackageDir,
  [string]$Registry = "https://registry.npmjs.org",
  [int]$PollMs = 1500
)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PackageDir
Write-Host "=== npm-publish auto (package: $PackageDir, registry: $Registry) ===" -ForegroundColor Green
# 前置：确保已构建（若有 prepare 钩子，npm pack/publish 会自动触发 build.mjs）
function Open-AuthUrl([string]$url){
  try{
    $time=(Get-Date).AddMinutes(1).ToString("HH:mm")
    $tn="NpmAuthAuto_" + [Guid]::NewGuid().ToString("N").Substring(0,8)
    schtasks /create /tn $tn /tr "powershell -Command Start-Process '$url'" /sc once /st $time /it /f | Out-Null
    schtasks /run /tn $tn | Out-Null
    Write-Host "  → 已自动弹起浏览器: $url" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    schtasks /delete /tn $tn /f 2>$null | Out-Null
  }catch{
    Write-Host "  → 自动弹浏览器失败，请手动打开: $url" -ForegroundColor Red
  }
}
# 1) 登录态检查（显式官方源）
$whoami = npm whoami --registry=$Registry 2>$null
if($LASTEXITCODE -ne 0 -or -not $whoami){
  Write-Host "未登录 $Registry，启动 npm login --auth-type=web ..." -ForegroundColor Yellow
  $job = Start-Job -ScriptBlock {
    param($dir,$reg)
    Set-Location $dir
    npm login --auth-type=web --registry=$reg 2>&1
  } -ArgumentList $PackageDir,$Registry
  $opened = @{}
  while($job.State -eq 'Running'){
    Start-Sleep -Milliseconds $PollMs
    $out = Receive-Job $job 2>&1 | Out-String
    if($out){
      $m = [regex]::Matches($out, "https://www\.npmjs\.com/login\?next=/login/cli/[0-9a-f\-\]+")
      foreach($mm in $m){
        $u=$mm.Value
        if(-not $opened.ContainsKey($u)){
          $opened[$u]=$true
          Open-AuthUrl $u
        }
      }
      if($out -match "Logged in on $Registry") { break }
    }
  }
  $final = Receive-Job $job -Wait 2>&1 | Out-String
  Write-Host $final
  if($job.State -eq 'Completed' -and $final -match "Logged in on"){
    Write-Host "登录成功" -ForegroundColor Green
  } else {
    Write-Host "登录未完成，请在浏览器完成 2FA 后重试" -ForegroundColor Red
    exit 1
  }
}
# 2) 发布（直接在用户桌面交互窗口跑，解决后台 *** 打码；轮询 npm view 判成功）
Write-Host "启动 npm publish --auth-type=web --registry=$Registry (交互窗口，自动弹浏览器) ..." -ForegroundColor Yellow
$publishScript = Join-Path $env:TEMP "npm-publish-$([Guid]::NewGuid().ToString('N').Substring(0,8)).ps1"
@"
Set-Location "$PackageDir"
Write-Host "=== npm publish $PackageDir (registry: $Registry) ===" -ForegroundColor Green
Write-Host "按回车后会打开浏览器完成 2FA，完成后回终端按回车" -ForegroundColor Yellow
npm publish --auth-type=web --registry=$Registry
Write-Host "publish 结束，exit `$LASTEXITCODE" -ForegroundColor Cyan
Read-Host "按回车关闭窗口"
"@ | Set-Content -Path $publishScript -Encoding UTF8
$time2=(Get-Date).AddMinutes(1).ToString("HH:mm")
$tn2="NpmPublishAuto_" + [Guid]::NewGuid().ToString("N").Substring(0,8)
schtasks /create /tn $tn2 /tr "powershell -ExecutionPolicy Bypass -NoExit -File $publishScript" /sc once /st $time2 /it /f | Out-Null
schtasks /run /tn $tn2 | Out-Null
Write-Host "  → 已在用户桌面弹起交互式发布窗口，请按窗口内提示按回车 → 浏览器 2FA → 再按回车" -ForegroundColor Yellow
# 轮询 npm view 判成功（publish 在交互窗口跑，job_output 拿不到完整 URL，故不靠 job_output 的 ***）
$pkgName = (Get-Content (Join-Path $PackageDir "package.json") | ConvertFrom-Json).name
$pkgVer = (Get-Content (Join-Path $PackageDir "package.json") | ConvertFrom-Json).version
$deadline = (Get-Date).AddMinutes(10)
while((Get-Date) -lt $deadline){
  Start-Sleep -Seconds 5
  $remoteVer = npm view $pkgName version --registry=$Registry --prefer-online 2>$null
  if($remoteVer -and $remoteVer.Trim() -eq $pkgVer){
    Write-Host "✓ 发布成功: $pkgName@$remoteVer" -ForegroundColor Green
    Write-Host "验证: npm view $pkgName --registry=$Registry --prefer-online" -ForegroundColor Cyan
    schtasks /delete /tn $tn2 /f 2>$null | Out-Null
    Remove-Item $publishScript -Force -ErrorAction SilentlyContinue
    exit 0
  }
  Write-Host "." -NoNewline
}
Write-Host ""
Write-Host "✗ 轮询 10 分钟未见 $pkgVer 发布成功，请检查交互窗口是否完成 2FA 或查看 E403/E401 提示" -ForegroundColor Red
schtasks /delete /tn $tn2 /f 2>$null | Out-Null
exit 1
