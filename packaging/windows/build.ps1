#Requires -Version 5.1
<#
.SYNOPSIS
  Build Terminal Radio for Windows (PyInstaller onedir + optional mpv).

.EXAMPLE
  .\packaging\windows\build.ps1
  .\packaging\windows\build.ps1 -DownloadMpv
  .\packaging\windows\build.ps1 -BuildInstaller
#>
param(
    [switch]$DownloadMpv,
    [switch]$BuildInstaller
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$DistDir = Join-Path $Root "dist\TerminalRadio"
$MpvDir = Join-Path $DistDir "mpv"
$ZipPath = Join-Path $Root "dist\TerminalRadio-win64.zip"

Set-Location $Root

Write-Host "==> Terminal Radio - Windows build" -ForegroundColor Cyan

Write-Host "  Installing PyInstaller + project..."
python -m pip install -q pyinstaller .

Write-Host "==> PyInstaller (onedir)"
python -m PyInstaller packaging/windows/radio.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path $DistDir)) {
    Write-Error "Expected output at $DistDir"
}

$RadioExe = Join-Path $DistDir "radio.exe"
$AliasExe = Join-Path $DistDir "terminal-radio.exe"
if (Test-Path $RadioExe) {
    Copy-Item $RadioExe $AliasExe -Force
}

function Install-MpvFromScoop {
    $scoopMpv = Join-Path $env:USERPROFILE "scoop\apps\mpv\current\mpv.exe"
    if (-not (Test-Path $scoopMpv)) {
        return $false
    }
    New-Item -ItemType Directory -Force -Path $MpvDir | Out-Null
    Copy-Item $scoopMpv (Join-Path $MpvDir "mpv.exe") -Force
    Write-Host "  [ok] mpv copied from Scoop"
    return $true
}

function Install-MpvBundled {
    Write-Host "==> Bundling mpv"
    if (Install-MpvFromScoop) { return }
    Write-Host "[error] mpv not found for bundling." -ForegroundColor Red
    Write-Host "  scoop bucket add extras; scoop install mpv" -ForegroundColor Yellow
    Write-Host ('  Or copy mpv.exe to: ' + $MpvDir + '\mpv.exe') -ForegroundColor Yellow
    exit 1
}

$mpvPresent = Test-Path (Join-Path $MpvDir "mpv.exe")
if (-not $mpvPresent -and $DownloadMpv) {
    Install-MpvBundled
} elseif (-not $mpvPresent) {
    Write-Host "[aviso] mpv\mpv.exe not found. Run with -DownloadMpv or copy mpv.exe manually." -ForegroundColor Yellow
}

Write-Host "==> Zip archive"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $DistDir -DestinationPath $ZipPath -Force
Write-Host ('  ' + $ZipPath)

if ($BuildInstaller) {
    $Iscc = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $Iscc) {
        Write-Host "[aviso] Inno Setup not found. Install from https://jrsoftware.org/isinfo.php" -ForegroundColor Yellow
    } else {
        Write-Host "==> Inno Setup installer"
        & $Iscc (Join-Path $PSScriptRoot "terminal-radio.iss")
        Write-Host "  dist\TerminalRadio-setup.exe"
    }
}

Write-Host ""
Write-Host "Done. Run:" -ForegroundColor Green
Write-Host ('  ' + $RadioExe)
