@echo off
setlocal

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

python generate_dbfs.py

streamlit run streamlit_app.py --server.port 8501
