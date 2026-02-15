import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match

def check_specific_matches():
    league = League.objects.filter(name__icontains='Brasileir').first()
    
    flamengo = Team.objects.filter(name='Flamengo', league=league).first()
    sao_paulo = Team.objects.filter(name='Sao Paulo', league=league).first() # Need to check exact name
    
    if not sao_paulo:
        # Try to find Sao Paulo
        sao_paulo = Team.objects.filter(name__icontains='Sao Paulo', league=league).first()
        
    print(f"Flamengo: {flamengo}")
    print(f"Sao Paulo: {sao_paulo}")
    
    if flamengo and sao_paulo:
        matches = Match.objects.filter(
            league=league,
            home_team=flamengo,
            away_team=sao_paulo
        ) | Match.objects.filter(
            league=league,
            home_team=sao_paulo,
            away_team=flamengo
        )
        
        print(f"Matches between Flamengo and Sao Paulo ({matches.count()}):")
        for m in matches:
            print(f"  - {m.date} | {m.home_team} vs {m.away_team} | {m.home_score}-{m.away_score}")

if __name__ == "__main__":
    check_specific_matches()
