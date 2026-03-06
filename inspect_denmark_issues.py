
import os
import django
import sys
from django.db.models import Count, Min, Max

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import League, Match, LeagueStanding, Team, Season

def inspect():
    try:
        league = League.objects.get(name='Superliga', country='Dinamarca')
        print(f"League: {league.name} (ID: {league.id})")
        
        # 1. Check Seasons
        print("\n--- Seasons ---")
        # Get distinct season IDs from matches for this league
        season_ids = Match.objects.filter(league=league).values_list('season', flat=True).distinct()
        seasons = Season.objects.filter(id__in=season_ids).order_by('year')
        
        for s in seasons:
            match_count = Match.objects.filter(league=league, season=s).count()
            standing_count = LeagueStanding.objects.filter(league=league, season=s).count()
            print(f"Season {s.year}: {match_count} matches, {standing_count} teams in standings.")
            
            # Check for matches with incorrect dates for the season
            if s.year == 2026:
                # Should be July 2025 - June 2026
                early = Match.objects.filter(league=league, season=s, date__lt='2025-06-01').count()
                late = Match.objects.filter(league=league, season=s, date__gt='2026-07-01').count()
                if early > 0: print(f"  WARNING: {early} matches before June 2025 in Season 2026")
                if late > 0: print(f"  WARNING: {late} matches after July 2026 in Season 2026")

        # 2. Check Standings for 2026 (Current)
        print("\n--- Standings 2026 (Current) ---")
        standings_2026 = LeagueStanding.objects.filter(league=league, season__year=2026).order_by('-played')
        for s in standings_2026:
            print(f"{s.team.name}: {s.played} games, {s.points} pts")

        # 3. Check "May" matches
        print("\n--- May Matches Analysis ---")
        # May 2025 (Should be end of Season 2025)
        may_2025 = Match.objects.filter(league=league, date__year=2025, date__month=5)
        print(f"Matches in May 2025: {may_2025.count()}")
        for m in may_2025[:3]:
            print(f"  {m.date} {m.home_team.name} vs {m.away_team.name} (Season: {m.season.year})")
            
        # May 2026 (Should be end of Season 2026 - Future/Current)
        may_2026 = Match.objects.filter(league=league, date__year=2026, date__month=5)
        print(f"Matches in May 2026: {may_2026.count()}")
        for m in may_2026[:3]:
            print(f"  {m.date} {m.home_team.name} vs {m.away_team.name} (Season: {m.season.year})")

        # 4. Check Duplicate Teams
        print("\n--- Team List ---")
        teams = Team.objects.filter(league=league).annotate(
            match_count=Count('home_matches') + Count('away_matches')
        ).order_by('name')
        
        for t in teams:
            print(f"ID {t.id}: {t.name} ({t.match_count} total matches)")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
