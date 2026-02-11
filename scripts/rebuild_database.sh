#!/bin/bash

# Script para reconstruir o banco de dados da Premier League
# Útil quando os dados estão inconsistentes ou desatualizados

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Ativar virtualenv
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "=================================================="
echo "INICIANDO RECONSTRUÇÃO DA PREMIER LEAGUE"
echo "Data: $(date)"
echo "=================================================="

# Executar o comando de reconstrução
# Ajuste o --year se necessário (2026 para temporada 25/26)
python3 manage.py rebuild_league "Premier League" --year 2026

echo "=================================================="
echo "PROCESSO FINALIZADO"
echo "=================================================="
