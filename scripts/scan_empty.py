import os
import sys

def scan_for_empty_names(directory):
    print(f"Escaneando: {directory}")
    for root, dirs, files in os.walk(directory):
        for f in files:
            bn = os.path.basename(f)
            if not bn or bn == '':
                print(f"!!! ENCONTRADO: Arquivo com basename vazio: '{os.path.join(root, f)}'")
        for d in dirs:
            bn = os.path.basename(d)
            if not bn or bn == '':
                print(f"!!! ENCONTRADO: Diretório com basename vazio: '{os.path.join(root, d)}'")

if __name__ == '__main__':
    # Verificar a pasta de times e a static global
    scan_for_empty_names('/www/wwwroot/statsfut.com/static/')
    # Tentar ver se há algo no nível do projeto
    scan_for_empty_names('/www/wwwroot/statsfut.com/')
