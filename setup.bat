@echo off
echo =========================================
echo   Diario Inteligente — Setup
echo =========================================

echo.
echo [1/3] Verificando Python...
python --version || (echo ERRO: Python nao encontrado! && pause && exit /b 1)

echo.
echo [2/3] Criando ambiente virtual...
if not exist venv (
    python -m venv venv
    echo Venv criada com sucesso!
) else (
    echo Venv ja existe, pulando criacao.
)

echo.
echo [3/3] Instalando dependencias...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo =========================================
echo   Setup concluido!
echo   Execute start.bat para iniciar.
echo =========================================
pause
