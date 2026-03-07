from matches.models import League, Match, Season
from django.db.models import Count

def inspect():
    try:
        league = League.objects.get(country='Austria', name='Bundesliga')
        print(f"=== Inspecting {league} ===")
        
        seasons = Season.objects.filter(matches__league=league).distinct().order_by('year')
        
        print(f"{'Season':<8} | {'Matches':<8} | {'Teams':<5} | {'First Date':<12} | {'Last Date':<12}")
        print("-" * 60)
        
        for s in seasons:
            qs = Match.objects.filter(league=league, season=s)
            count = qs.count()
            
            teams = set(qs.values_list('home_team__name', flat=True)) | set(qs.values_list('away_team__name', flat=True))
            teams_count = len(teams)
            
            first = qs.order_by('date').first()
            last = qs.order_by('date').last()
            
            f_date = first.date.strftime('%Y-%m-%d') if first and first.date else "None"
            l_date = last.date.strftime('%Y-%m-%d') if last and last.date else "None"
            
            print(f"{s.year:<8} | {count:<8} | {teams_count:<5} | {f_date:<12} | {l_date:<12}")
            
            if count < 50:
                print(f"  ⚠️  WARNING: Very few matches for {s.year}!")
                print(f"  Teams found: {sorted(list(teams))}")

    except League.DoesNotExist:
        print("League Austria/Bundesliga not found")

if __name__ == "__main__":
    inspect()
