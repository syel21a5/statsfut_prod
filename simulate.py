import sys
import os
import django
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q

# Configure Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "statsfut.settings")
django.setup()

from matches.models import Match
from matches.services.advanced_stats import MatchAnalyzer

def simulate():
    # Pick recent finished matches so we have historical data before them
    end_date = timezone.now()
    start_date = end_date - timedelta(days=10) # last 10 days of matches
    
    matches = Match.objects.filter(
        date__range=(start_date, end_date),
        status__in=['FT', 'Finished', 'Match Finished']
    ).select_related('home_team', 'away_team')[:1000] # Limit to 1000 to keep it fast

    print(f"Simulating {matches.count()} matches from the last 10 days...")

    stats = {
        'OVER_15': {'hits': 0, 'total': 0},
        'OVER_25': {'hits': 0, 'total': 0},
        'HT_GOAL': {'hits': 0, 'total': 0},
        'BTTS': {'hits': 0, 'total': 0},
    }

    for match in matches:
        try:
            if match.home_score is None or match.away_score is None:
                continue
            
            analyzer = MatchAnalyzer(match)
            if len(analyzer.home_last_10) < 6 or len(analyzer.away_last_10) < 6:
                continue
            
            goals = analyzer.get_goal_markets() or {}
            
            home_len = len(analyzer.home_last_10)
            away_len = len(analyzer.away_last_10)
            
            home_over25_pct = int((sum(1 for m in analyzer.home_last_10 if m.home_score is not None and (m.home_score + m.away_score) > 2.5) / home_len) * 100) if home_len > 0 else 0
            away_over25_pct = int((sum(1 for m in analyzer.away_last_10 if m.home_score is not None and (m.home_score + m.away_score) > 2.5) / away_len) * 100) if away_len > 0 else 0
            home_btts_pct = int((sum(1 for m in analyzer.home_last_10 if m.home_score is not None and m.home_score > 0 and m.away_score > 0) / home_len) * 100) if home_len > 0 else 0
            away_btts_pct = int((sum(1 for m in analyzer.away_last_10 if m.home_score is not None and m.home_score > 0 and m.away_score > 0) / away_len) * 100) if away_len > 0 else 0
            
            total_goals = match.home_score + match.away_score
            has_ht_goal = False
            if match.ht_home_score is not None and match.ht_away_score is not None:
                has_ht_goal = (match.ht_home_score + match.ht_away_score) > 0
            else:
                has_ht_goal = match.goals.filter(minute__lte=45).exists()

            has_btts = match.home_score > 0 and match.away_score > 0
            
            # Test OVER 1.5 at 88% threshold
            if goals.get('over_15', 0) >= 88:
                stats['OVER_15']['total'] += 1
                if total_goals >= 2: stats['OVER_15']['hits'] += 1
            
            # Test OVER 2.5 at 80% threshold + 70% history
            if goals.get('over_25', 0) >= 80 and home_over25_pct >= 70 and away_over25_pct >= 70:
                stats['OVER_25']['total'] += 1
                if total_goals >= 3: stats['OVER_25']['hits'] += 1

            # Test HT GOAL at 88% threshold
            if goals.get('ht_goal', 0) >= 88:
                stats['HT_GOAL']['total'] += 1
                if has_ht_goal: stats['HT_GOAL']['hits'] += 1

            # Test BTTS at 80% threshold + 70% history
            if goals.get('btts', 0) >= 80 and home_btts_pct >= 70 and away_btts_pct >= 70:
                stats['BTTS']['total'] += 1
                if has_btts: stats['BTTS']['hits'] += 1

        except Exception as e:
            continue

    print("\n--- SIMULATION RESULTS ---")
    for market, data in stats.items():
        if data['total'] > 0:
            winrate = (data['hits'] / data['total']) * 100
            print(f"{market}: {data['hits']}/{data['total']} hits ({winrate:.1f}%)")
        else:
            print(f"{market}: 0 tips generated")

if __name__ == '__main__':
    simulate()
