#!/bin/sh
set -e

# Aguardar o banco de dados estar pronto
echo "Aguardando banco de dados ($DB_HOST:$DB_PORT)..."
while ! python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.connect(('$DB_HOST', int('$DB_PORT')))" 2>/dev/null; do
  echo "Aguardando MySQL em $DB_HOST:$DB_PORT..."
  sleep 2
done
echo "Banco de dados iniciado!"

# Rodar migrações
echo "Aplicando migrações..."
python manage.py migrate

# Coletar estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Iniciar o Tor com ControlPort habilitado (para rotação de IP)
echo "Configurando Tor com ControlPort..."
grep -q "^ControlPort 9051" /etc/tor/torrc || echo "ControlPort 9051" >> /etc/tor/torrc
grep -q "^CookieAuthentication 0" /etc/tor/torrc || echo "CookieAuthentication 0" >> /etc/tor/torrc
grep -q "^MaxCircuitDirtiness 10" /etc/tor/torrc || echo "MaxCircuitDirtiness 10" >> /etc/tor/torrc
echo "Iniciando serviço do Tor..."
service tor start || tor &
sleep 5

# Executar o comando passado pelo Docker (respeita o command do docker-compose)
echo "Iniciando aplicação com comando: $@"
exec "$@"
