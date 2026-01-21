@echo off
setlocal

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

python generate_dbfs.py

streamlit run streamlit_app.py --server.port 8501
