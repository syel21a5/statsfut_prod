from django.core.management import call_command
from matches.models import League, Season, LeagueStanding

try:
    league = League.objects.get(name='Bundesliga', country='Austria')
    print(f"League found: {league}")
    
    seasons = Season.objects.filter(matches__league=league).distinct()
    years = sorted([s.year for s in seasons])
    print(f"Seasons found with matches: {years}")
    
    for year in years:
        print(f"Recalculating standings for {year}...")
        try:
            # Chama o comando de gerenciamento existente
            call_command('recalculate_standings', league_name='Bundesliga', country='Austria', season_year=year)
            
            # Verifica se criou
            s_obj = Season.objects.filter(year=year).first()
            if s_obj:
                count = LeagueStanding.objects.filter(league=league, season=s_obj).count()
                print(f"  -> Standings count for {year}: {count}")
        except Exception as e:
            print(f"Error calculating for {year}: {e}")

    print("Done.")

except League.DoesNotExist:
    print("League 'Bundesliga' (Austria) not found.")
except Exception as e:
    print(f"Error: {e}")
