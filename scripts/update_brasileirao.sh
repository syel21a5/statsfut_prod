#!/bin/bash

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/update_brasileirao.log"

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Navigate to project root
cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "========================================" >> "$LOG_FILE"
echo "Starting Brasileirão update at $(date)" >> "$LOG_FILE"

# 1. Run SoccerStats Scraper (Substitui Sofascore)
echo "Running scrape_soccerstats_brazil..." >> "$LOG_FILE"
python manage.py scrape_soccerstats_brazil >> "$LOG_FILE" 2>&1

# 2. Run Duplicate Fix (Safety Check)
# echo "Running fix_brasileirao_final..." >> "$LOG_FILE"
# python manage.py fix_brasileirao_final >> "$LOG_FILE" 2>&1

# 3. Recalculate Standings
echo "Recalculating standings..." >> "$LOG_FILE"
python manage.py recalculate_standings --league_name "Brasileirão" >> "$LOG_FILE" 2>&1

echo "Update finished at $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
