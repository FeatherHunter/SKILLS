# ============================================================
# login-window.ps1 - npm login (web approval flow, interactive)
#   Part of npm-publish skill flow: login first, then publish
# ============================================================
$Host.UI.RawUI.WindowTitle = 'DSH npm login'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ''
Write-Host '============================================================'
Write-Host '  DSH npm login window (skill flow: step 3)'
Write-Host '============================================================'
Write-Host ''
Write-Host '  1. Press ENTER -> npm login starts'
Write-Host '  2. See "Authenticate your account at: <URL>"'
Write-Host '  3. Press ENTER -> browser opens npm auth page'
Write-Host '  4. Login + 2FA confirm in browser'
Write-Host '  5. Back to window, press ENTER again'
Write-Host '  Success: npm whoami outputs your username'
Write-Host '============================================================'
Write-Host ''
Read-Host 'Press ENTER to start npm login'
npm login --registry=https://registry.npmjs.org
Write-Host ''
Write-Host '--- verify ---'
npm whoami --registry=https://registry.npmjs.org 2>&1
Write-Host ('whoami exit: ' + $LASTEXITCODE)
if ($LASTEXITCODE -eq 0) {
    Write-Host 'LOGIN OK - now tell Agent to launch publish window'
} else {
    Write-Host 'LOGIN FAILED - copy this window to Agent'
}
Write-Host ''
Read-Host 'Press ENTER to close'
