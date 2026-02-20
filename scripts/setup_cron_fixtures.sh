#!/bin/bash

# Define paths
# Baseado na estrutura do servidor: /www/wwwroot/statsfut.com
PROJECT_DIR="/www/wwwroot/statsfut.com"
VENV_ACTIVATE="$PROJECT_DIR/venv/bin/activate"
LOG_FILE="$PROJECT_DIR/cron_fixtures.log"

# The command to run the standalone script
# We need to be in the project dir so imports work correctly
CMD_SCRAPE="cd $PROJECT_DIR && source $VENV_ACTIVATE && python matches/scrapers/argentina/scrape_fixtures.py >> $LOG_FILE 2>&1"

# Add Cron Job (Run every 6 hours: 0 */6 * * *)
# Isso garante que a lista de jogos futuros seja atualizada 4 vezes ao dia
(crontab -l 2>/dev/null | grep -F "scrape_fixtures.py") && echo "Cronjob de fixtures já existe." || {
    (crontab -l 2>/dev/null; echo "0 */6 * * * $CMD_SCRAPE") | crontab -
    echo "Cronjob de fixtures adicionado (A cada 6 horas)."
}

echo "Configuração do cron Fixtures concluída!"
echo "Log será salvo em: $LOG_FILE"
