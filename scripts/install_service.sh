#!/bin/bash
# Script para facilitar a configuração do serviço de monitoramento no Linux

echo ">>> Iniciando configuração do Serviço de Monitoramento..."

# 1. Copiar o arquivo de serviço para o diretório do systemd
if [ -f "scripts/statsfut-live.service" ]; then
    echo ">>> Copiando arquivo de serviço..."
    cp scripts/statsfut-live.service /etc/systemd/system/
else
    echo "ERRO: Arquivo scripts/statsfut-live.service não encontrado!"
    exit 1
fi

# 2. Recarregar o daemon do systemd
echo ">>> Recarregando daemon do systemd..."
systemctl daemon-reload

# 3. Habilitar o serviço para iniciar no boot
echo ">>> Habilitando serviço para iniciar no boot..."
systemctl enable statsfut-live.service

# 4. Iniciar o serviço agora
echo ">>> Iniciando o serviço..."
systemctl start statsfut-live.service

# 5. Verificar status
echo ">>> Verificando status do serviço:"
systemctl status statsfut-live.service --no-pager

echo ""
echo ">>> Instalação Concluída! 🚀"
echo "O robô está rodando em segundo plano e vai reiniciar automaticamente se o servidor reiniciar."
echo "Para ver logs em tempo real, use: journalctl -u statsfut-live.service -f"
