#!/bin/bash

# Define diretório do projeto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Cria diretório de logs se não existir
mkdir -p logs

echo "=================================================="
echo "INICIANDO SISTEMA DE ATUALIZAÇÃO AUTOMÁTICA"
echo "Data: $(date)"
echo "=================================================="

# Ativa ambiente virtual se existir
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 1. Mata processos antigos para evitar duplicidade
echo "Parando processos antigos..."
pkill -f "run_live_updates.py"
pkill -f "run_csv_updates.py"
sleep 2

# 2. Inicia atualização de APIs (Live + Upcoming)
echo "Iniciando run_live_updates.py..."
nohup python3 run_live_updates.py > logs/api_updates.log 2>&1 &
PID_LIVE=$!
echo "✅ run_live_updates.py iniciado (PID $PID_LIVE)"

# 3. Inicia atualização de CSV (Diária 03:00)
echo "Iniciando run_csv_updates.py..."
nohup python3 run_csv_updates.py > logs/csv_updates.log 2>&1 &
PID_CSV=$!
echo "✅ run_csv_updates.py iniciado (PID $PID_CSV)"

echo "=================================================="
echo "SISTEMA RODANDO EM BACKGROUND"
echo "Logs disponíveis em:"
echo "  - logs/api_updates.log"
echo "  - logs/csv_updates.log"
echo "=================================================="
