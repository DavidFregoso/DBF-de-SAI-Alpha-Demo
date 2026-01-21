@echo off
setlocal

if not exist .venv (
  py -3.11 -m venv .venv
  if errorlevel 1 (
    python -m venv .venv
  )
)

call .venv\Scripts\activate
python -m pip install -U pip setuptools wheel
if errorlevel 1 exit /b 1
pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 (
  echo Use Python 3.11 x64
  exit /b 1
)

python generate_dbfs.py

streamlit run streamlit_app.py --server.port 8501
