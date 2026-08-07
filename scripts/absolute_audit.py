import os
import sys
import django # type: ignore

sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, LeagueStanding, League, Season # type: ignore
from django.db import transaction # type: ignore

def absolute_audit():
    print("=== AUDITORIA ABSOLUTA DE DADOS (VPS) ===")

    # 1. Identificar a Liga e Temporada que o site está usando
    # O usuário está em /stats/brazil/
    country_name = 'Brasil'
    league = League.objects.filter(country__icontains=country_name, name__icontains='Brasileira').first()
    
    if not league:
        print("!! ERRO: Liga não encontrada.")
        return
        
    print(f"-> Liga Selecionada: {league.name} (ID: {league.id})")
    
    latest_season = league.standings.order_by('-season__year').first().season if league.standings.exists() else None
    print(f"-> Temporada mais recente no Standings: {latest_season.year if latest_season else 'N/A'}")

    # 2. Listar TODOS os times da tabela (sem filtros de ano se possível, para ver se há lixo)
    print("\n[Times na Tabela Atual]")
    standings = LeagueStanding.objects.filter(league=league, season=latest_season).order_by('position')
    print(f"Total na QuerySet: {standings.count()}")
    
    for s in standings:
        t = s.team
        print(f"Pos {s.position:2} | ID {t.id:4} | Name: {t.name:25} | API: {t.api_id}")

    # 3. Investigar TODOS os Bragantinos e Remos do sistema inteiro
    print("\n[Busca Global por Nomes Conflitantes]")
    for name in ['Bragantino', 'Remo', 'São Paulo']:
        print(f"\nBusca por '{name}':")
        teams = Team.objects.filter(name__icontains=name)
        for t in teams:
            stds = LeagueStanding.objects.filter(team=t)
            leagues = [f"L:{st.league_id}-S:{st.season.year}" for st in stds]
            print(f" -> ID {t.id:4} | API: {t.api_id:10} | League Corrente: {t.league_id} | Standings: {leagues}")

    # 4. Verificar se existe outro "Brasil" ou "Brasileirão"
    print("\n[Verificando Duplicidade de Ligas/Países]")
    all_brasils = League.objects.filter(country__icontains='Brasil')
    for l in all_brasils:
        print(f" -> Liga ID {l.id} | Name: {l.name} | Country: {l.country}")

if __name__ == '__main__':
    absolute_audit()
