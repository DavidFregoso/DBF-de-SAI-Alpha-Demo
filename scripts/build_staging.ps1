param(
    [string]$PythonVersion = "",
    [string]$Architecture = "amd64"
)

$ErrorActionPreference = "Stop"

$requiredArchitecture = "64bit"

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if (-not $pyLauncher) {
    throw "Python launcher (py) not found. Install Python 3.11 x64 to build the installer."
}

$pyInfo = & py -3.11 -c "import platform, sys; print(sys.version.split()[0]); print(platform.architecture()[0])" 2>$null
if ($LASTEXITCODE -ne 0 -or -not $pyInfo) {
    throw "Python 3.11 not found via 'py -3.11'. Install Python 3.11 x64 to build the installer."
}

$pyVersion = $pyInfo[0]
$pyArch = $pyInfo[1]
if (-not $pyVersion.StartsWith("3.11.") -or $pyArch -ne $requiredArchitecture) {
    throw "Python 3.11 x64 is required. Detected $pyVersion $pyArch via 'py -3.11'."
}

if ([string]::IsNullOrWhiteSpace($PythonVersion)) {
    $PythonVersion = $pyVersion
}

if (-not $PythonVersion.StartsWith("3.11.")) {
    throw "PythonVersion must be 3.11.x for the embeddable runtime. Received $PythonVersion."
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$buildDir = Join-Path $repoRoot "build"
$stagingDir = Join-Path $buildDir "staging"
$runtimeDir = Join-Path $stagingDir "runtime"
$appDir = Join-Path $stagingDir "app"

if (Test-Path $stagingDir) {
    Remove-Item -Path $stagingDir -Recurse -Force
}

New-Item -ItemType Directory -Path $runtimeDir | Out-Null
New-Item -ItemType Directory -Path $appDir | Out-Null
$dbfDir = Join-Path $appDir "data\dbf"
New-Item -ItemType Directory -Path $dbfDir -Force | Out-Null

$pythonZip = Join-Path $buildDir "python-embed.zip"
$pythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-$Architecture.zip"

Write-Host "Downloading Python embeddable runtime from $pythonUrl"
Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip

Write-Host "Extracting Python runtime to $runtimeDir"
Expand-Archive -Path $pythonZip -DestinationPath $runtimeDir -Force

$versionParts = $PythonVersion.Split(".")
$pyMajorMinor = "{0}{1}" -f $versionParts[0], $versionParts[1]
$pthFile = Join-Path $runtimeDir ("python{0}._pth" -f $pyMajorMinor)

if (-not (Test-Path $pthFile)) {
    throw "Unable to locate $pthFile in embedded runtime."
}

Write-Host "Patching embedded Python path file at $pthFile"
$updatedContent = @(
    "python$pyMajorMinor.zip",
    "..\\app",
    "Lib\\site-packages",
    "import site"
)

$updatedContent | Set-Content -Path $pthFile -Encoding ASCII

$getPip = Join-Path $buildDir "get-pip.py"
Write-Host "Downloading get-pip.py"
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip

Write-Host "Installing pip into embedded runtime"
& (Join-Path $runtimeDir "python.exe") $getPip --no-warn-script-location

Write-Host "Installing Python dependencies"
& (Join-Path $runtimeDir "python.exe") -m pip install --no-cache-dir -r (Join-Path $repoRoot "requirements.txt")

Write-Host "Copying app files"
Copy-Item -Path (Join-Path $repoRoot "app.py") -Destination (Join-Path $appDir "app.py")
Copy-Item -Path (Join-Path $repoRoot "generate_dbfs.py") -Destination (Join-Path $appDir "generate_dbfs.py")
Copy-Item -Path (Join-Path $repoRoot "sai_alpha") -Destination (Join-Path $appDir "sai_alpha") -Recurse
if (Test-Path (Join-Path $repoRoot "pages")) {
    Copy-Item -Path (Join-Path $repoRoot "pages") -Destination (Join-Path $appDir "pages") -Recurse
}

$startDemoPath = Join-Path $stagingDir "StartDemo.cmd"
@"
@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "RUNTIME_DIR=%SCRIPT_DIR%runtime"
set "APP_DIR=%SCRIPT_DIR%app"
set "PYTHON_EXE=%RUNTIME_DIR%\python.exe"

if not exist "%PYTHON_EXE%" (
  echo Embedded Python not found at %PYTHON_EXE%.
  echo Please reinstall the demo.
  pause
  exit /b 1
)

set "DBF_DIR=%APP_DIR%\data\dbf"
if not exist "%DBF_DIR%" mkdir "%DBF_DIR%"
set "SAI_DBF_DIR=%DBF_DIR%"
echo DBF dir: %SAI_DBF_DIR%

set "DBF_COUNT=0"
for /f %%A in ('dir /b "%DBF_DIR%\*.dbf" 2^>nul') do set /a DBF_COUNT+=1
if !DBF_COUNT! LSS 1 (
  echo Generating mock DBF data...
  pushd "%APP_DIR%" >nul
  "%PYTHON_EXE%" "generate_dbfs.py"
  if errorlevel 1 (
    echo Failed to generate DBF data.
    popd >nul
    pause
    exit /b 1
  )
  popd >nul
)

set "PORT="
for /l %%P in (8501,1,8510) do (
  for /f %%A in ('powershell -NoProfile -Command "Test-NetConnection -ComputerName 127.0.0.1 -Port %%P -InformationLevel Quiet"') do set "PORT_IN_USE=%%A"
  if /i "!PORT_IN_USE!"=="False" (
    set "PORT=%%P"
    goto :port_found
  )
)

:port_found
if not defined PORT (
  echo No free port found between 8501 and 8510.
  pause
  exit /b 1
)

set "LAN_IP="
for /f %%A in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '169.254*' -and $_.IPAddress -ne '127.0.0.1' } | Select-Object -First 1 -ExpandProperty IPAddress)"') do set "LAN_IP=%%A"
if not defined LAN_IP set "LAN_IP=127.0.0.1"

echo Starting Streamlit on http://127.0.0.1:%PORT%
echo LAN access: http://%LAN_IP%:%PORT%
start "" "http://127.0.0.1:%PORT%"

pushd "%APP_DIR%" >nul
"%PYTHON_EXE%" -m streamlit run "app.py" --server.address 0.0.0.0 --server.port %PORT%
popd >nul

endlocal
"@ | Set-Content -Path $startDemoPath -Encoding ASCII

if (-not (Test-Path $startDemoPath)) {
    throw "StartDemo.cmd was not created in staging."
}
if (-not (Test-Path $dbfDir)) {
    throw "DBF directory missing at $dbfDir."
}
$pipExe = Join-Path $runtimeDir "Scripts\\pip.exe"
if (-not (Test-Path $pipExe)) {
    throw "pip was not installed into the embedded runtime."
}
& (Join-Path $runtimeDir "python.exe") -m pip show streamlit *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Streamlit was not installed into the embedded runtime."
}

Write-Host "Staging folder ready at $stagingDir"
Write-Host "Run command: $(Join-Path $stagingDir "StartDemo.cmd")"
