#!/bin/sh

# Aguardar o banco de dados estar pronto
echo "Aguardando banco de dados..."
# while ! nc -z $DB_HOST $DB_PORT; do
#   sleep 0.5
# done
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
