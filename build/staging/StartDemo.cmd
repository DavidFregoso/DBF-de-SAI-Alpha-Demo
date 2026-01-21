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

set "HAS_DBF="
for /f %%A in ('dir /b "%DBF_DIR%\*.dbf" 2^>nul') do set "HAS_DBF=1"
if not defined HAS_DBF (
  echo Generating mock DBF data...
  pushd "%APP_DIR%" >nul
  "%PYTHON_EXE%" "%APP_DIR%\generate_dbfs.py"
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

echo Starting Streamlit on http://127.0.0.1:%PORT%
start "" "http://127.0.0.1:%PORT%"

pushd "%APP_DIR%" >nul
"%PYTHON_EXE%" -m streamlit run "%APP_DIR%\app.py" --server.address 127.0.0.1 --server.port %PORT%
popd >nul

endlocal
