import os
import shutil

def fix_windows_paths(base_dir):
    print(f"Buscando por pastas/arquivos com contra-barra em: {base_dir}")
    fixed_count = 0
    
    # Precisamos iterar múltiplas vezes porque renomear diretórios no meio do os.walk pode confundi-lo,
    # ou podemos apenas procurar tudo que tem "\\" e corrigir de baixo para cima.
    
    items_to_fix = []
    
    for root, dirs, files in os.walk(base_dir):
        for d in dirs:
            if '\\' in d:
                items_to_fix.append(os.path.join(root, d))
        for f in files:
            if '\\' in f:
                items_to_fix.append(os.path.join(root, f))
                
    if not items_to_fix:
        print("Nenhuma contra-barra encontrada!")
        return
        
    for bad_path in items_to_fix:
        if not os.path.exists(bad_path): continue
        
        # bad_path: /www/.../static/teams/alemanha\bundesliga
        parent_dir = os.path.dirname(bad_path)
        bad_name = os.path.basename(bad_path)
        
        # bad_name = "alemanha\bundesliga"
        # Precisamos transformar em alemanha/bundesliga
        parts = bad_name.split('\\')
        
        # O novo caminho final
        dest_path = os.path.join(parent_dir, *parts)
        
        # Criar os diretórios pais necessários
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        print(f"Movendo: '{bad_path}' -> '{dest_path}'")
        shutil.move(bad_path, dest_path)
        fixed_count += 1  # type: ignore[operator]
        
    print(f"Concluído! {fixed_count} caminhos corrigidos.")

if __name__ == '__main__':
    fix_windows_paths('/www/wwwroot/statsfut.com/static/')
