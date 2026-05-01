@echo off
echo =========================================
echo   Diario Inteligente — Backend FastAPI
echo =========================================
call venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
