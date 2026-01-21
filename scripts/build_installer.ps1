$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$installerScript = Join-Path $repoRoot "build\installer.iss"

if (-not (Test-Path $installerScript)) {
    throw "Installer script not found at $installerScript"
}

$possiblePaths = @(
    $env:INNO_SETUP_PATH,
    "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe",
    "C:\\Program Files\\Inno Setup 6\\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) }

if ($possiblePaths.Count -eq 0) {
    throw "ISCC.exe not found. Set INNO_SETUP_PATH or install Inno Setup 6."
}

$iscc = $possiblePaths[0]
Write-Host "Using Inno Setup Compiler: $iscc"
& $iscc $installerScript
