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
# 2. Corrige times duplicados conhecidos (ex: Nottingham -> Nottm Forest)
# ---------------------------------------------------
log "Corrigindo times duplicados..."
$PYTHON $MANAGE shell -c "
from matches.models import Team, League, Match
fixes = [
    ('Inglaterra', 'Premier League', 'Nottingham', 'Nottm Forest'),
]
for country, league_name, wrong, correct in fixes:
    try:
        league = League.objects.get(name=league_name, country=country)
        wrong_team = Team.objects.filter(name=wrong, league=league).first()
        correct_team = Team.objects.filter(name=correct, league=league).first()
        if wrong_team and correct_team:
            h = Match.objects.filter(home_team=wrong_team).update(home_team=correct_team)
            a = Match.objects.filter(away_team=wrong_team).update(away_team=correct_team)
            wrong_team.delete()
            print(f'Corrigido: {wrong} -> {correct} ({h} home, {a} away)')
        else:
            print(f'OK: {wrong} nao encontrado ou {correct} nao existe')
    except Exception as e:
        print(f'Erro em {league_name}: {e}')
" >> "$LOG" 2>&1

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
