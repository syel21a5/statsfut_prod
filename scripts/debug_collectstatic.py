import os
import sys

# Preparar o ambiente Django
sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django # type: ignore
django.setup()

from django.core.management import call_command # type: ignore
import django.core.files.utils as utils # type: ignore

print("=== INICIANDO COLLECTSTATIC COM DEPURAÇÃO NINJA ===")

# Salvar a função original
original_validate = utils.validate_file_name

# Mapeamento do hack para dedurar o arquivo
def hacked_validate(name, allow_relative_path=False):
    try:
        # Tenta validar normalmente
        return original_validate(name, allow_relative_path)
    except Exception as e:
        # Se der erro, ELE GRITA O NOME DO ARQUIVO ANTES DE MORRER
        print(f"\n\n{'='*50}")
        print(f"🚨 ACHEI O CULPADO! 🚨")
        print(f"O Django tentou salvar um arquivo/pasta com o nome exatamente igual a: '{name}'")
        print(f"Tamanho do nome: {len(name)} caracteres.")
        print(f"Representação bruta: {repr(name)}")
        print(f"{'='*50}\n\n")
        raise e

# Injetar o hack
utils.validate_file_name = hacked_validate

# Rodar o collectstatic
try:
    call_command('collectstatic', interactive=False, verbosity=1)
except Exception as final_fatal:
    print(f"\nCollectstatic parou devido a: {final_fatal}")
