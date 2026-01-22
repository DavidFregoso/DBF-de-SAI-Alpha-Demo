@echo off
setlocal EnableExtensions EnableDelayedExpansion

if not exist .venv (
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo Python 3.11 x64 is required. Install it and rerun.
    exit /b 1
  )
)

call .venv\Scripts\activate
python -m pip install -U pip setuptools wheel
if errorlevel 1 exit /b 1
pip install -r requirements.txt
if errorlevel 1 exit /b 1

set "DBF_DIR=%CD%\data\dbf"
if not exist "%DBF_DIR%" mkdir "%DBF_DIR%"
set "SAI_ALPHA_DBF_DIR=%DBF_DIR%"

set "DBF_COUNT=0"
for /f %%A in ('dir /b "%DBF_DIR%\*.dbf" 2^>nul') do set /a DBF_COUNT+=1
if %DBF_COUNT% LSS 1 (
  echo Generating mock DBF data...
  python generate_dbfs.py
  if errorlevel 1 exit /b 1
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
  exit /b 1
)

set "LAN_IP="
for /f %%A in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '169.254*' -and $_.IPAddress -ne '127.0.0.1' } | Select-Object -First 1 -ExpandProperty IPAddress)"') do set "LAN_IP=%%A"
if not defined LAN_IP set "LAN_IP=127.0.0.1"

echo Starting Streamlit on http://127.0.0.1:%PORT%
echo LAN access: http://%LAN_IP%:%PORT%
start "" "http://127.0.0.1:%PORT%"

streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port %PORT%
