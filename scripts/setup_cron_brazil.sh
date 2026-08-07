#!/bin/bash

# Define paths
PROJECT_DIR="/www/wwwroot/statsfut.com"
VENV_ACTIVATE="$PROJECT_DIR/venv/bin/activate"
LOG_FILE="$PROJECT_DIR/cron_brazil.log"

# Define commands
# Run scraper at minute 0 every hour
CMD_SCRAPE="cd $PROJECT_DIR && source $VENV_ACTIVATE && python manage.py scrape_api_football_brazil >> $LOG_FILE 2>&1"
# Run recalculate at minute 5 every hour (after scraper)
CMD_CALC="cd $PROJECT_DIR && source $VENV_ACTIVATE && python manage.py recalculate_standings --league_name 'Brasileirão' --season_year 2026 >> $LOG_FILE 2>&1"

# Add Scraper Job
(crontab -l 2>/dev/null | grep -F "scrape_api_football_brazil") && echo "Cronjob do scraper já existe." || {
    (crontab -l 2>/dev/null; echo "0 * * * * $CMD_SCRAPE") | crontab -
    echo "Cronjob do scraper adicionado (roda a cada hora no minuto 0)."
}

# Add Recalculate Job
(crontab -l 2>/dev/null | grep -F "recalculate_standings --league_name 'Brasileirão'") && echo "Cronjob de recálculo já existe." || {
    (crontab -l 2>/dev/null; echo "5 * * * * $CMD_CALC") | crontab -
    echo "Cronjob de recálculo adicionado (roda a cada hora no minuto 5)."
}

echo "Configuração do cron concluída! O robô vai rodar automaticamente."
