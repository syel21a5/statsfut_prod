#!/bin/bash

# Define paths
# Baseado na estrutura do servidor: /www/wwwroot/statsfut.com
PROJECT_DIR="/www/wwwroot/statsfut.com"
VENV_ACTIVATE="$PROJECT_DIR/venv/bin/activate"
LOG_FILE="$PROJECT_DIR/cron_fixtures.log"

# The command to run the standalone script
# We need to be in the project dir so imports work correctly
CMD_SCRAPE_FIXTURES="cd $PROJECT_DIR && source $VENV_ACTIVATE && python matches/scrapers/argentina/scrape_fixtures.py >> $LOG_FILE 2>&1"
CMD_SCRAPE_RESULTS="cd $PROJECT_DIR && source $VENV_ACTIVATE && python matches/scrapers/argentina/scrape_results.py >> $LOG_FILE 2>&1"

# Add Cron Job for Fixtures (Run every 6 hours: 0 */6 * * *)
# Isso garante que a lista de jogos futuros seja atualizada 4 vezes ao dia
(crontab -l 2>/dev/null | grep -F "scrape_fixtures.py") && echo "Cronjob de fixtures já existe." || {
    (crontab -l 2>/dev/null; echo "0 */6 * * * $CMD_SCRAPE_FIXTURES") | crontab -
    echo "Cronjob de fixtures adicionado (A cada 6 horas)."
}

# Add Cron Job for Results (Run every 2 hours: 0 */2 * * *)
# Isso garante que os resultados recentes sejam capturados logo após os jogos
(crontab -l 2>/dev/null | grep -F "scrape_results.py") && echo "Cronjob de results já existe." || {
    (crontab -l 2>/dev/null; echo "0 */2 * * * $CMD_SCRAPE_RESULTS") | crontab -
    echo "Cronjob de results adicionado (A cada 2 horas)."
}

echo "Configuração do cron Fixtures & Results concluída!"
echo "Log será salvo em: $LOG_FILE"
