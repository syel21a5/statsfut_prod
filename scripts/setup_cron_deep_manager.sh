#!/bin/bash

# Define paths
PROJECT_DIR="/www/wwwroot/statsfut.com"
VENV_ACTIVATE="$PROJECT_DIR/venv/bin/activate"
LOG_FILE="$PROJECT_DIR/cron_smart_deep_manager.log"

echo "=================================================="
echo " CONFIGURANDO O SMART DEEP MANAGER (VPS)"
echo "=================================================="

# Verifica se o Tor está instalado
if ! command -v tor &> /dev/null; then
    echo "Tor não encontrado. Instalando..."
    sudo apt-get update
    sudo apt-get install -y tor
    echo "Tor instalado com sucesso."
else
    echo "Tor já está instalado."
fi

# Garante que o serviço do Tor inicie automaticamente
sudo systemctl enable tor
sudo systemctl start tor

# Permissão para o usuário atual conseguir reiniciar o Tor (opcional se rodar como root)
# O script Python vai rodar um 'systemctl restart tor' se for bloqueado.
# Como o cron será configurado para rodar como root na VPS, isso funcionará nativamente.

# Define command
# Roda a cada 2 horas no minuto 15 (ex: 00:15, 02:15, 04:15)
CMD_DEEP="cd $PROJECT_DIR && source $VENV_ACTIVATE && python manage.py smart_deep_manager >> $LOG_FILE 2>&1"

# Add Job
(crontab -l 2>/dev/null | grep -F "smart_deep_manager") && echo "Cronjob do Smart Deep Manager já existe." || {
    (crontab -l 2>/dev/null; echo "15 */2 * * * $CMD_DEEP") | crontab -
    echo "✅ Cronjob adicionado (A cada 2 horas, minuto 15)."
}

echo "=================================================="
echo " Concluído! O sistema baixará os dados faltantes "
echo " da temporada atual a cada 2 horas silenciosamente."
echo "=================================================="
