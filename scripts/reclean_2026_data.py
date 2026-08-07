import os
import sys
import django  # type: ignore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, League, Season, LeagueStanding  # type: ignore
from django.db import transaction  # type: ignore

def reclean():
    countries = ['Brasil', 'Suica', 'Belgica']
    year = 2026
    
    print(f"=== INICIANDO LIMPEZA DE DADOS 2026 ({', '.join(countries)}) ===\n")

    try:
        season = Season.objects.get(year=year)
    except Season.DoesNotExist:
        print(f"Erro: Temporada {year} não encontrada.")
        return

    with transaction.atomic():
        for country in countries:
            print(f"Processando {country}...")
            leagues = League.objects.filter(country__icontains=country)
            for league in leagues:
                # Deleta partidas da temporada 2026 para esta liga
                matches_deleted, _ = Match.objects.filter(league=league, season=season).delete()
                # Deleta classificações da temporada 2026
                standings_deleted, _ = LeagueStanding.objects.filter(league=league, season=season).delete()
                
                print(f"  Liga: {league.name}")
                print(f"    - Partidas deletadas: {matches_deleted}")
                print(f"    - Classificações deletadas: {standings_deleted}")

    print("\n=== LIMPEZA CONCLUÍDA ===")
    print("Agora você deve rodar os comandos de importação normal.")

if __name__ == "__main__":
    reclean()
