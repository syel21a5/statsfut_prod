import os
import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

print(f"Django Version: {django.get_version()}")
print(f"Database Engine: {settings.DATABASES['default']['ENGINE']}")

try:
    import MySQLdb
    print("MySQLdb (ou emulado) carregado com sucesso.")
except ImportError:
    print("MySQLdb NÃO encontrado.")

try:
    import pymysql
    print("PyMySQL encontrado.")
except ImportError:
    print("PyMySQL NÃO encontrado.")

from django.db import connection
print(f"Connection Vendor: {connection.vendor}")

if connection.vendor == 'sqlite':
    print("\n--- ATENÇÃO ---")
    print("O Django está usando SQLite. Verifique os logs acima para erros de importação.")
else:
    print("\n--- SUCESSO ---")
    print("Django conectado ao MySQL!")
