#!/bin/bash
echo "========================================="
echo "  Diario Inteligente — Frontend Angular"
echo "========================================="
cd frontend
echo "Buildando e observando mudanças... (Ctrl+C ou feche o terminal para parar)"
npm run build -- --watch
