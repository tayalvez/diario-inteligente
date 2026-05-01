@echo off
echo =========================================
echo   Diario Inteligente — Iniciando...
echo =========================================
echo.

if not exist venv (
    echo ERRO: Venv nao encontrada. Execute setup.bat primeiro.
    pause
    exit /b 1
)

echo [1/2] Iniciando backend FastAPI (porta 8000)...
start "Backend FastAPI" cmd /k "venv\Scripts\activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Aguardando backend inicializar...
timeout /t 3 /nobreak >nul

echo [2/2] Iniciando frontend Angular (porta 4200)...
start "Frontend Angular" cmd /k "cd frontend && npm start"

echo.
echo =========================================
echo   Aplicacao rodando!
echo   Backend: http://localhost:8000
echo   Frontend: http://localhost:4200
echo   API Docs: http://localhost:8000/docs
echo =========================================
echo   Feche as duas janelas para parar.
pause
