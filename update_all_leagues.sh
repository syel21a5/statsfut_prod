#!/bin/bash
# =======================================================
# update_all_leagues.sh
# Atualiza todas as ligas via CSV do football-data.co.uk
# Rodar via cron job no BT Panel (diariamente às 03:00)
# =======================================================

PROJECT_DIR="/www/wwwroot/statsfut.com"
PYTHON="$PROJECT_DIR/venv/bin/python"
MANAGE="$PROJECT_DIR/manage.py"
LOG="$PROJECT_DIR/logs/csv_update.log"
MIN_YEAR=2025

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

log "========== INICIANDO ATUALIZAÇÃO CSV =========="

# ---------------------------------------------------
# 1. Importa CSVs de cada liga com dados
# ---------------------------------------------------

import_league() {
    local division=$1
    local name=$2
    log "Importando: $name ($division)..."
    $PYTHON $MANAGE import_football_data --division "$division" --min_year $MIN_YEAR >> "$LOG" 2>&1
    if [ $? -eq 0 ]; then
        log "✓ $name importada com sucesso"
    else
        log "✗ Erro ao importar $name"
    fi
}

import_league "E0"  "Premier League"
import_league "SP1" "La Liga"
import_league "I1"  "Serie A"
import_league "D1"  "Bundesliga"
import_league "F1"  "Ligue 1"
import_league "N1"  "Eredivisie"
import_league "P1"  "Primeira Liga"
import_league "BRA" "Brasileirao"
import_league "ARG" "Liga Profesional"
import_league "CZE" "First League"

# ---------------------------------------------------
# 2. Corrige times duplicados (nome errado → nome correto via TEAM_NAME_MAPPINGS)
# ---------------------------------------------------
log "Corrigindo times duplicados..."
$PYTHON $MANAGE resolve_duplicate_teams >> "$LOG" 2>&1
if [ $? -eq 0 ]; then
    log "✓ Times duplicados corrigidos"
else
    log "✗ Erro ao corrigir duplicados"
fi

# ---------------------------------------------------
# 3. Recalcula tabelas de todas as ligas
# ---------------------------------------------------
log "Recalculando standings..."

recalc() {
    local name=$1
    local country=$2
    log "  Tabela: $name..."
    $PYTHON $MANAGE recalculate_standings --league_name "$name" --country "$country" >> "$LOG" 2>&1
}

recalc "Premier League"   "Inglaterra"
recalc "La Liga"          "Espanha"
recalc "Serie A"          "Italia"
recalc "Bundesliga"       "Alemanha"
recalc "Ligue 1"          "Franca"
recalc "Eredivisie"       "Holanda"
recalc "Primeira Liga"    "Portugal"
recalc "Brasileirao"      "Brasil"
recalc "Liga Profesional" "Argentina"
recalc "First League"     "Republica Tcheca"

log "========== ATUALIZAÇÃO CONCLUÍDA =========="
