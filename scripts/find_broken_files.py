import os
import sys
import django # type: ignore
from django.core.exceptions import SuspiciousFileOperation # type: ignore
from django.core.files.utils import validate_file_name # type: ignore

sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def find_malformed_files(directory):
    print(f"Buscando arquivos malformados em: {directory}")
    found = False
    for root, dirs, files in os.walk(directory):
        # Checar se o nome do diretório é válido
        dir_name = os.path.basename(root)
        if dir_name:
            try:
                validate_file_name(dir_name)
            except SuspiciousFileOperation:
                print(f"!! DIRETÓRIO INVÁLIDO detectado: '{root}'")
                found = True

        for file in files:
            try:
                # O Django verifica o nome do arquivo individualmente
                validate_file_name(file)
            except SuspiciousFileOperation:
                full_path = os.path.join(root, file)
                print(f"!! ARQUIVO INVÁLIDO detectado: '{full_path}' (Nome: '{file}')")
                found = True
            except Exception as e:
                print(f"Erro ao validar {file}: {e}")

    if not found:
        print("Nenhum arquivo malformado óbvio encontrado pelo validador do Django.")
    return found

if __name__ == '__main__':
    # Verificar tanto a pasta de times quanto a static inteira
    find_malformed_files('/www/wwwroot/statsfut.com/static/')
