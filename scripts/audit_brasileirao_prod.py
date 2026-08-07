import os
import sys
import django # type: ignore
from django.utils.text import slugify # type: ignore

sys.path.append('/www/wwwroot/statsfut.com')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, LeagueStanding, Match, League, Season # type: ignore
from django.db.models import Q # type: ignore

def final_audit():
    print("=== AUDITORIA CIRÚRGICA 2.0: BRASILEIRÃO (PRODUÇÃO) ===")
    
    # Listar as Ligas
    print("\n[Ligas Brasileiras]")
    l_bras = League.objects.filter(country__icontains='Brasil', name__icontains='Brasileira')
    for l in l_bras:
        s_count = LeagueStanding.objects.filter(league=l).count()
        t_count = Team.objects.filter(league=l).count()
        print(f" -> ID: {l.id} | Name: {l.name} | Standings: {s_count} | Teams: {t_count}")

    # Listar as Classificações (Standings) por Temporada
    print("\n[Classificações por Temporada]")
    standings = LeagueStanding.objects.filter(
        league__country__icontains='Brasil', 
        league__name__icontains='Brasileira'
    ).select_related('team', 'league', 'season').order_by('season__year', 'position')

    print(f"\nYear | Pos | Team (ID) | API_ID | League ID")
    print("-" * 70)
    
    for s in standings:
        t = s.team
        aid = str(t.api_id) if t.api_id else "NONE"
        print(f"{s.season.year} | {s.position:2} | {t.name[:20]:20} ({t.id:4}) | {aid:10} | L:{s.league_id}")

    # Investigar REMO e BRAGANTINO
    for query_name in ['Remo', 'Bragantino']:
        print(f"\n[Foco: {query_name}]")
        ts = Team.objects.filter(name__icontains=query_name)
        for t in ts:
            games = Match.objects.filter(Q(home_team=t) | Q(away_team=t)).count()
            stds = LeagueStanding.objects.filter(team=t)
            print(f" -> ID: {t.id} | Name: {t.name} | API: {t.api_id} | League: {t.league.name} (ID: {t.league_id}) | Games: {games}")
            for sd in stds:
                print(f"    - Standing in L:{sd.league_id} | S:{sd.season.year} | Pos:{sd.position}")

if __name__ == '__main__':
    final_audit()
