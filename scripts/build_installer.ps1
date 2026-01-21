$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$buildScript = Join-Path $repoRoot "scripts\build_staging.ps1"
$stagingDir = Join-Path $repoRoot "build\staging"
$distDir = Join-Path $repoRoot "dist"

Write-Host "Building staging folder..."
& powershell -NoProfile -ExecutionPolicy Bypass -File $buildScript

if (-not (Test-Path $stagingDir)) {
    throw "Staging folder was not created at $stagingDir"
}

if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir | Out-Null
}

$zipPath = Join-Path $distDir "DBF-SAI-Alpha-Demo-Portable.zip"
if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

Write-Host "Creating portable ZIP at $zipPath"
Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath -Force

Write-Host "Portable ZIP ready: $zipPath"
