#!/bin/bash
echo "========================================="
echo "  Diario Inteligente — Setup"
echo "========================================="

echo ""
echo "[1/3] Verificando Python..."
python3 --version || { echo "ERRO: Python nao encontrado!"; exit 1; }

echo ""
echo "[2/3] Criando ambiente virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Venv criada com sucesso!"
else
    echo "Venv ja existe, pulando criacao."
fi

echo ""
echo "[3/3] Instalando dependencias..."
source venv/bin/activate
pip install -r requirements.txt

echo ""
echo "========================================="
echo "  Setup concluido!"
echo "  Execute ./start.sh para iniciar."
echo "========================================="
