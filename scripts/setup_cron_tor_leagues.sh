#!/bin/bash
# ===========================================================
# setup_cron_tor_leagues.sh
# Configura cron job para atualizar ligas secundárias via Tor
# Roda a cada 8 horas (3x por dia) na VPS
# ===========================================================

PROJECT_DIR="/www/wwwroot/statsfut.com"
VENV_ACTIVATE="$PROJECT_DIR/venv/bin/activate"
LOG_FILE="$PROJECT_DIR/logs/cron_tor_leagues.log"

echo "=================================================="
echo " CONFIGURANDO ATUALIZAÇÃO DE LIGAS SECUNDÁRIAS VIA TOR"
echo "=================================================="

# Cria diretório de logs se não existir
mkdir -p "$PROJECT_DIR/logs"

# 1. Verifica se o Tor está instalado e ativo
if ! command -v tor &> /dev/null; then
    echo "Tor não encontrado. Instalando..."
    sudo apt-get update
    sudo apt-get install -y tor
    echo "Tor instalado com sucesso."
else
    echo "✅ Tor já está instalado."
fi

sudo systemctl enable tor
sudo systemctl start tor
echo "✅ Serviço do Tor ativo e configurado para iniciar no boot."

# 2. Configura o cron job
# Roda a cada 8 horas nos minutos 30 (ex: 00:30, 08:30, 16:30)
# Isso evita conflito com o update_all_leagues.sh (03:00) e o smart_deep_manager (*/2h minuto 15)
CMD_TOR="cd $PROJECT_DIR && source $VENV_ACTIVATE && python manage.py tor_league_updater >> $LOG_FILE 2>&1"

(crontab -l 2>/dev/null | grep -F "tor_league_updater") && echo "Cronjob das ligas secundárias já existe." || {
    (crontab -l 2>/dev/null; echo "30 */8 * * * $CMD_TOR") | crontab -
    echo "✅ Cronjob adicionado! Roda a cada 8 horas (00:30, 08:30, 16:30)."
}

echo ""
echo "=================================================="
echo " CONFIGURAÇÃO CONCLUÍDA!"
echo "=================================================="
echo ""
echo " Frequência: A cada 8 horas (3x por dia)"
echo " Horários:   00:30, 08:30, 16:30"
echo " Log:        $LOG_FILE"
echo " Comando:    python manage.py tor_league_updater"
echo ""
echo " Para testar manualmente:"
echo "   cd $PROJECT_DIR"
echo "   source venv/bin/activate"
echo "   python manage.py tor_league_updater"
echo ""
echo " Para atualizar apenas a Championship:"
echo "   python manage.py tor_league_updater --league championship"
echo ""
echo " Para fazer full scan (todas as rodadas):"
echo "   python manage.py tor_league_updater --full-scan"
echo "=================================================="
