import os
import sys
import django # type: ignore

sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League, LeagueStanding # type: ignore

def check_prod():
    output_path = '/www/wwwroot/statsfut.com/diag_output.txt'
    with open(output_path, 'w') as f:
        f.write("--- DIAGNÓSTICO PRODUÇÃO ---\n")
        
        # 1. Verificar Flamengo
        t = Team.objects.filter(name__icontains='Flamengo').first()
        if t:
            f.write(f"Flamengo: {t.name} (ID: {t.id}) | api_id: {t.api_id}\n")
        else:
            f.write("Flamengo não encontrado!\n")

        # 2. Verificar Bragantinos
        brants = Team.objects.filter(name__icontains='Bragantino')
        f.write(f"\nEncontrados {brants.count()} times com 'Bragantino':\n")
        for b in brants:
            f.write(f" - {b.id} | {b.name} | api_id: {b.api_id} | League: {b.league.name} (ID: {b.league_id})\n")

        # 3. Standings
        standings = LeagueStanding.objects.filter(league__name__icontains='Brasileira', season__year=2025).order_by('position')
        f.write(f"\nStandings do Brasileirão 2025 (Total: {standings.count()}):\n")
        for s in standings:
            f.write(f" - Pos {s.position}: {s.team.name} (ID: {s.team_id})\n")
    
    print(f"Relatório salvo em {output_path}")

if __name__ == '__main__':
    check_prod()
