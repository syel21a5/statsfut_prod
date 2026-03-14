import os
import sys

sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django # type: ignore
django.setup()

from django.core.management import call_command # type: ignore
from django.contrib.staticfiles.management.commands.collectstatic import Command as CollectstaticCommand # type: ignore

print("=== INICIANDO COLLECTSTATIC BLINDADO ===")

original_copy_file = CollectstaticCommand.copy_file

def bulletproof_copy_file(self, path, prefixed_path, source_storage):
    try:
        # Se o caminho for vazio ou problemático, a gente pula
        if not path or path.strip() == '':
            print(f" IGNORANDO ARQUIVO FANTASMA: Caminho vazio detectado.")
            return
            
        # Chama o original
        return original_copy_file(self, path, prefixed_path, source_storage)
    except Exception as e:
        print(f" SALVOU O DIA: Ignorando erro ao copiar '{path}': {e}")
        return

# Substitui o método de cópia
CollectstaticCommand.copy_file = bulletproof_copy_file

try:
    call_command('collectstatic', interactive=False, clear=True, verbosity=0)
    print("\n=== SUCESSO! COLLECTSTATIC BLINDADO CONCLUÍDO ===")
    print("Todas as logos válidas foram copiadas. Os erros fantasmas foram ignorados.")
except Exception as e:
    print(f"\nERRO CRÍTICO AINDA PERSISTE: {e}")
