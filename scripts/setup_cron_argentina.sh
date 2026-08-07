#!/bin/bash

# Define paths
PROJECT_DIR="/www/wwwroot/statsfut.com"
VENV_ACTIVATE="$PROJECT_DIR/venv/bin/activate"
LOG_FILE="$PROJECT_DIR/cron_argentina.log"

# Define commands
# Run import for Argentina at minute 30 every Monday and Thursday (football-data updates)
# But since we want it "fresh", maybe daily?
# football-data says "updated twice weekly". Let's run it daily at 04:00 AM to be safe.
CMD_IMPORT="cd $PROJECT_DIR && source $VENV_ACTIVATE && python manage.py import_football_data --division ARG --min_year 2026 >> $LOG_FILE 2>&1"
# Run recalculate at 04:05 AM
CMD_CALC="cd $PROJECT_DIR && source $VENV_ACTIVATE && python manage.py recalculate_standings --league_name 'Liga Profesional' --season_year 2026 >> $LOG_FILE 2>&1"

# Add Import Job
(crontab -l 2>/dev/null | grep -F "import_football_data --division ARG") && echo "Cronjob da Argentina já existe." || {
    (crontab -l 2>/dev/null; echo "0 4 * * * $CMD_IMPORT") | crontab -
    echo "Cronjob de importação Argentina adicionado (Diário às 04:00)."
}

# Add Recalculate Job
(crontab -l 2>/dev/null | grep -F "recalculate_standings --league_name 'Liga Profesional'") && echo "Cronjob de recálculo Argentina já existe." || {
    (crontab -l 2>/dev/null; echo "5 4 * * * $CMD_CALC") | crontab -
    echo "Cronjob de recálculo Argentina adicionado (Diário às 04:05)."
}

echo "Configuração do cron Argentina concluída!"
