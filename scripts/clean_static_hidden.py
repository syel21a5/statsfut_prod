import os
import shutil

def clean_hidden_files(directory):
    print(f"Limpando arquivos ocultos/inválidos em: {directory}")
    removed_count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Remover arquivos ocultos (começam com .) ou arquivos que criam nomes vazios
            if file.startswith('.') or file == '':
                path = os.path.join(root, file)
                try:
                    os.remove(path)
                    print(f" Removido: {path}")
                    removed_count += 1
                except Exception as e:
                    print(f" Erro ao remover {path}: {e}")
                    
        # Remover diretórios ocultos (ex: .DS_Store)
        for d in dirs[:]:
            if d.startswith('.'):
                path = os.path.join(root, d)
                try:
                    shutil.rmtree(path)
                    print(f" Removido diretório: {path}")
                    dirs.remove(d) # Evita tentar caminhar por ele
                except Exception as e:
                    print(f" Erro ao remover diretório {path}: {e}")

    print(f"Limpeza concluída. {removed_count} arquivos problemáticos removidos.")

if __name__ == '__main__':
    target = '/www/wwwroot/statsfut.com/static/teams/'
    if os.path.exists(target):
        clean_hidden_files(target)
    else:
        print(f"Diretório não encontrado: {target}")
