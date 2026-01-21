#!/bin/bash

# ==========================================
# Script de Deploy Automatizado para aaPanel
# ==========================================

# Configurações
PROJECT_DIR=$(pwd)
ENV_FILE=".env"
COMPOSE_FILE="docker-compose.prod.yml"

echo "=== Iniciando Deploy em $(date) ==="

# 1. Tratamento do Arquivo Imortal (.user.ini)
# O aaPanel cria este arquivo e o bloqueia. Precisamos desbloquear para evitar erros de permissão.
if [ -f ".user.ini" ]; then
    echo "🔓 Desbloqueando .user.ini..."
    chattr -i .user.ini
fi

# 2. Backup do .env (Regra de Ouro #3)
if [ -f "$ENV_FILE" ]; then
    echo "📦 Fazendo backup do .env..."
    cp $ENV_FILE "${ENV_FILE}.backup"
else
    echo "⚠️ .env não encontrado! Certifique-se de criá-lo antes de rodar os containers."
    # Opcional: Criar um .env padrão se não existir
    # echo "DEBUG=False" > .env
fi

# 3. Pull das últimas alterações (se estiver usando git)
if [ -d ".git" ]; then
    echo "⬇️ Atualizando código via Git..."
    git pull origin main
else
    echo "ℹ️ Repositório Git não detectado, pulando git pull."
fi

# 4. Limpeza e Rebuild (Regra de Ouro #3 - Clean Install)
# Verifica se o usuário quer uma instalação limpa (passar argumento 'clean')
if [ "$1" == "clean" ]; then
    echo "🧹 Execução LIMPA solicitada (apagando volumes)..."
    docker compose -f $COMPOSE_FILE down -v
else
    echo "🔄 Reiniciando containers (mantendo dados)..."
    docker compose -f $COMPOSE_FILE down
fi

# 5. Build e Subida
echo "🚀 Construindo e subindo containers..."
docker compose -f $COMPOSE_FILE up -d --build

# 6. Verificação
echo "🔍 Verificando status..."
docker compose -f $COMPOSE_FILE ps

echo "=== Deploy Concluído! ==="
echo "🌍 App rodando na porta 8081 (Mapeada para 8000 interna)"
echo "⚠️  Não esqueça de configurar o Reverse Proxy no aaPanel para http://127.0.0.1:8081"
echo "🔗 Domínio esperado: teste1.statsfut.com"
