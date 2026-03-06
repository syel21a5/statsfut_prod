"""
Script executado pelo GitHub Actions para:
1. Exportar os dados da Austrália do banco local (SQLite de CI)
2. Fazer upload do fixture para o servidor de produção via SSH
3. Importar os dados no servidor de produção com loaddata
"""
import os
import django
import json
import subprocess
import sys

# Usa as settings de CI (SQLite)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings_ci')
django.setup()

from django.core.serializers import serialize
from matches.models import League, Team, Match, Season, LeagueStanding

def export_and_upload():
    print("=== Exportando dados da Austrália ===")
    league = League.objects.filter(name__icontains='A-League', country__icontains='Australia').first()
    if not league:
        print("ERRO: Liga da Austrália não encontrada. O scraper falhou?")
        sys.exit(1)

    print(f"Liga: {league.name} | Partidas: {Match.objects.filter(league=league).count()}")

    # Serializar todos os objetos relacionados
    all_objects = []
    all_objects += list(League.objects.filter(id=league.id))
    season_ids = Match.objects.filter(league=league).values_list('season_id', flat=True).distinct()
    all_objects += list(Season.objects.filter(id__in=season_ids))
    all_objects += list(Team.objects.filter(league=league))
    all_objects += list(Match.objects.filter(league=league))
    all_objects += list(LeagueStanding.objects.filter(league=league))

    fixture_data = json.loads(serialize('json', all_objects))
    fixture_path = 'australia_fixture.json'
    with open(fixture_path, 'w', encoding='utf-8') as f:
        json.dump(fixture_data, f, ensure_ascii=False, indent=2)

    size_kb = os.path.getsize(fixture_path) / 1024
    print(f"Fixture gerado: {fixture_path} ({size_kb:.1f} KB)")

    # Variáveis de ambiente injetadas pelo GitHub Actions Secrets
    server_host = os.environ.get('PROD_SERVER_HOST', '')
    server_user = os.environ.get('PROD_SERVER_USER', 'root')
    server_path = os.environ.get('PROD_SERVER_PATH', '/www/wwwroot/statsfut.com')
    venv_python = f"{server_path}/venv/bin/python"

    if not server_host:
        print("AVISO: PROD_SERVER_HOST não configurado. Pulando upload.")
        print("Fixture salvo localmente em:", fixture_path)
        return

    print(f"\n=== Enviando fixture para {server_host} ===")

    # SCP para enviar o arquivo
    scp_cmd = [
        'scp', '-o', 'StrictHostKeyChecking=no',
        fixture_path,
        f"{server_user}@{server_host}:{server_path}/{fixture_path}"
    ]
    result = subprocess.run(scp_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ERRO no SCP:", result.stderr)
        sys.exit(1)
    print("Upload feito com sucesso!")

    # SSH para limpar a Austrália antiga e importar a nova
    print("\n=== Importando dados no servidor ===")
    ssh_cmd = [
        'ssh', '-o', 'StrictHostKeyChecking=no',
        f"{server_user}@{server_host}",
        f"cd {server_path} && "
        f"{venv_python} clear_australia.py && "
        f"{venv_python} manage.py loaddata {fixture_path} && "
        f"{venv_python} manage.py recalculate_standings --league_name 'A-League Men' --country 'Australia' --smart && "
        f"rm {fixture_path}"
    ]
    result = subprocess.run(ssh_cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("ERRO no SSH:", result.stderr)
        sys.exit(1)

    print("\n✅ Datos da Austrália atualizados no servidor com sucesso!")

if __name__ == '__main__':
    export_and_upload()
