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

# Iniciar Gunicorn
echo "Iniciando Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3
