# Builds the standalone Physiognomy.ai app into dist\Physiognomy\.
# Usage (from anywhere):  powershell -File packaging\build.ps1
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

& "$repo\venv\Scripts\python.exe" -m PyInstaller Physiognomy.spec --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }

# Stage the user-editable/user-visible files next to the exe. main.py looks
# for them relative to the exe when frozen.
$out = "$repo\dist\Physiognomy"
Copy-Item "$repo\config.yaml" $out -Force

if (Test-Path "$out\assets") { Remove-Item -Recurse -Force "$out\assets" }
Copy-Item "$repo\assets" "$out\assets" -Recurse

New-Item -ItemType Directory -Force "$out\models" | Out-Null
Copy-Item "$repo\models\*.task" "$out\models" -Force
Copy-Item "$repo\packaging\README-windows.txt" "$out\README.txt" -Force

Write-Host "`nBuild complete: $out\Physiognomy.exe"
