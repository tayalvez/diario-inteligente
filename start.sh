#!/bin/bash
echo "========================================="
echo "  Diario Inteligente — Iniciando..."
echo "========================================="
echo ""

if [ ! -d "venv" ]; then
    echo "ERRO: Venv nao encontrada. Execute ./setup.sh primeiro."
    exit 1
fi

echo "[1/2] Compilando frontend Angular..."
cd frontend && npm run build 2>&1 | tail -3
cd ..

echo ""
echo "[2/2] Iniciando backend FastAPI (porta 8000)..."
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo ""
echo "========================================="
echo "  Aplicacao rodando!"
echo "  Acesse: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "========================================="
echo "  Pressione Ctrl+C para parar."

wait $BACKEND_PID
