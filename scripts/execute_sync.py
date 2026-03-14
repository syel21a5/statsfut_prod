import os
import sys
import django # type: ignore
import subprocess
import zipfile
import shutil

sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings # type: ignore
from django.core.cache import cache # type: ignore

def run_sync():
    print("=== INICIANDO APLICAÇÃO DE SINCRONIZAÇÃO TOTAL ===")
    
    db_config = settings.DATABASES['default']
    db_name = db_config['NAME']
    db_user = db_config['USER']
    db_pass = db_config['PASSWORD']
    db_host = db_config['HOST']
    db_port = db_config['PORT']
    
    dump_file = "/www/wwwroot/statsfut.com/local_betstats_dump.sql"
    zip_file = "/www/wwwroot/statsfut.com/local_logos_backup.zip"
    
    # 1. Importar Banco de Dados
    if os.path.exists(dump_file):
        print(f"[1/3] Importando banco de dados para '{db_name}'...")
        # Construir comando mysql
        cmd = [
            'mysql',
            f'-h{db_host}',
            f'-P{db_port}',
            f'-u{db_user}',
            f'-p{db_pass}',
            db_name
        ]
        try:
            with open(dump_file, 'r') as f:
                subprocess.run(cmd, stdin=f, check=True)
            print(" ✓ Banco de dados importado com sucesso.")
        except subprocess.CalledProcessError as e:
            print(f" !! ERRO ao importar banco: {e}")
            return
    else:
        print(f" !! ERRO: Arquivo {dump_file} não encontrado.")
        return

    # 2. Substituir Logos
    if os.path.exists(zip_file):
        print("\n[2/3] Substituindo pasta de logos...")
        target_dir = "/www/wwwroot/statsfut.com/static/teams/"
        
        # Backup da pasta antiga (opcional mas seguro)
        backup_dir = "/www/wwwroot/statsfut.com/static/teams_backup_sync"
        if os.path.exists(target_dir):
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.move(target_dir, backup_dir)
            print(f" -> Pasta antiga movida para {backup_dir}")
        
        os.makedirs(target_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        print(" ✓ Novas logos extraídas com sucesso.")
    else:
        print(f" !! AVISO: {zip_file} não encontrado. Pulando etapa de logos.")

    # 3. Limpeza Geral
    print("\n[3/3] Limpando cache e finalizando...")
    cache.clear()
    
    # Reiniciar staticfiles se necessário (WhiteNoise pode precisar de collectstatic se mudamos nomes)
    print(" -> Rodando collectstatic para garantir paridade...")
    subprocess.run([sys.executable, 'manage.py', 'collectstatic', '--noinput'], check=True)
    
    print("\n=== SINCRONIZAÇÃO TOTAL CONCLUÍDA COM SUCESSO! ===")

if __name__ == '__main__':
    run_sync()
