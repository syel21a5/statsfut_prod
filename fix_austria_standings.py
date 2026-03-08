import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Season, LeagueStanding, Match

def clean_standings():
    league = League.objects.filter(country='Austria').first()
    if not league:
        print("Liga não encontrada")
        return

    # Ano com o problema relatado no print (2022/2023 -> year=2023)
    year = 2023 
    season = Season.objects.filter(year=year).first()
    
    if not season:
        print("Season não encontrada")
        return
        
    print(f"--- Limpando Classificações Fantasmas: {league.name} ({year-1}/{year}) ---")
    
    # Todos os times que realmente tiveram jogos nesta temporada
    matches = Match.objects.filter(league=league, season=season)
    valid_team_ids = set()
    for m in matches:
        if m.home_team_id: valid_team_ids.add(m.home_team_id)
        if m.away_team_id: valid_team_ids.add(m.away_team_id)

    # Identificar classificações (LeagueStanding) de times que NÃO jogaram
    standings = LeagueStanding.objects.filter(league=league, season=season)
    
    deleted_count = 0
    for st in standings:
        if st.team_id not in valid_team_ids:
            print(f"Removendo Standing FANTASMA do time: {st.team.name} (Nunca jogou nesta temp)")
            st.delete()
            deleted_count += 1
            
    if deleted_count == 0:
        print("Nenhum fantasma encontrado. Tudo parece limpo agora.")
    else:
        print(f"Total de classificações fantasmas removidas: {deleted_count}")

if __name__ == '__main__':
    clean_standings()
