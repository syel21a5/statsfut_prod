#!/bin/bash
set -e

echo "==============================================="
echo "   ☢️  INICIANDO LIMPEZA TOTAL E REINSTALAÇÃO"
echo "   (Isso vai apagar o banco atual e recriar)"
echo "==============================================="

# 1. Ir para o diretório
cd "$(dirname "$0")"

# 2. Atualizar código
echo "⬇️  Atualizando repositório..."
git fetch --all
git reset --hard origin/main
git pull origin main

# 3. Derrubar tudo E APAGAR VOLUMES (-v)
# Isso remove qualquer configuração antiga de banco de dados corrompida
echo "💥 Removendo containers e volumes antigos..."
docker compose -f docker-compose.prod.yml down -v --remove-orphans

# 4. Recriar .env com configuração limpa
echo "📝 Configurando ambiente..."
cat > .env <<EOF
DEBUG=False
SECRET_KEY=django-insecure-nucle-$(date +%s)
# Permitir tudo para evitar erro 400
ALLOWED_HOSTS=*
CSRF_TRUSTED_ORIGINS=https://teste1.statsfut.com,http://teste1.statsfut.com,http://localhost:8081
DB_NAME=betstats
DB_USER=root
DB_PASSWORD=root
DB_HOST=db
DB_PORT=3306
EOF

# 5. Permissões
chmod +x entrypoint.sh

# 6. Subir tudo do zero
echo "🚀 Iniciando novos containers..."
docker compose -f docker-compose.prod.yml up -d --build --force-recreate

echo "⏳ Aguardando Banco de Dados iniciar e importar dados (20s)..."
sleep 20

# 7. Verificar status
echo "🔍 Verificando status..."
if docker compose -f docker-compose.prod.yml ps | grep "Up"; then
    echo "==============================================="
    echo "   ✅ TUDO PRONTO! ACESSE: http://teste1.statsfut.com"
    echo "==============================================="
    echo "Logs do Web:"
    docker compose -f docker-compose.prod.yml logs --tail=10 web
else
    echo "❌ ALGO DEU ERRADO. Mostrando logs:"
    docker compose -f docker-compose.prod.yml logs --tail=20
fi
