@echo off
setlocal

set "PORT=8501"
if not "%~1"=="" set "PORT=%~1"

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if not exist "dbf\*.dbf" (
  python generate_mock_dbf.py
)

set "SERVER_IP=localhost"
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
  set "SERVER_IP=%%A"
  goto :got_ip
)
:got_ip
set "SERVER_IP=%SERVER_IP: =%"

echo Demo corriendo en: http://localhost:%PORT%
echo En red: http://%SERVER_IP%:%PORT%

streamlit run app.py --server.address 0.0.0.0 --server.port %PORT%

pause
