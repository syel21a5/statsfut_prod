from matches.models import League, Season, Match, LeagueStanding
from django.db.models import Count

def check_seasons():
    leagues = League.objects.all().order_by('country', 'name')
    
    print(f"{'Country':<20} | {'League':<30} | {'Year':<6} | {'Matches':<8} | {'Standings':<9} | {'Teams':<5}")
    print("-" * 90)
    
    for league in leagues:
        # Get all seasons associated with matches for this league
        seasons = Season.objects.filter(matches__league=league).distinct().order_by('year')
        
        if not seasons.exists():
             print(f"{league.country:<20} | {league.name:<30} | {'NO DATA':<6} | {'-':<8} | {'-':<9} | {'-':<5}")
             continue

        for season in seasons:
            match_count = Match.objects.filter(league=league, season=season).count()
            standing_count = LeagueStanding.objects.filter(league=league, season=season).count()
            
            # Count distinct teams in matches to compare with standings
            team_ids = set(Match.objects.filter(league=league, season=season).values_list('home_team_id', flat=True)) | \
                       set(Match.objects.filter(league=league, season=season).values_list('away_team_id', flat=True))
            teams_count = len(team_ids)
            
            status_symbol = "✅"
            if match_count < 10: status_symbol = "⚠️" # Too few matches
            if standing_count == 0: status_symbol = "❌" # No table
            if standing_count > 0 and standing_count != teams_count: status_symbol = "❓" # Mismatch teams vs table

            print(f"{league.country:<20} | {league.name:<30} | {season.year:<6} | {match_count:<8} | {standing_count:<9} | {teams_count:<5} {status_symbol}")

if __name__ == "__main__":
    check_seasons()
