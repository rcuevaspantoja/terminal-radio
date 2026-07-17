# Instalador Windows. Mismo install.py que Linux y macOS.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} else {
    Write-Error "Python 3.11+ no encontrado. Instálalo desde https://python.org"
    exit 1
}

& $pythonCmd scripts/install.py @args
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    $localBin = Join-Path $env:USERPROFILE ".local\bin"
    if (Test-Path $localBin) {
        $env:PATH = "$localBin;$env:PATH"
        Write-Host ""
        Write-Host "PATH de esta sesion actualizado. Prueba ahora: radio"
    }
}

exit $exitCode
