import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match, League, Team
from django.db.models import Q

def check_prod_data():
    print("--- Verificação Detalhada de Produção ---")
    
    # Austrália (ID 21)
    try:
        l_aus = League.objects.get(id=21)
        m_aus = Match.objects.filter(league=l_aus)
        print(f"Austrália (ID 21): {m_aus.count()} jogos totais")
        
        nj = Team.objects.get(name__icontains="Newcastle", league=l_aus)
        nj_matches = Match.objects.filter(Q(home_team=nj) | Q(away_team=nj)).order_by('date')
        print(f"\nJogos do Newcastle Jets ({nj.name}): {nj_matches.count()}")
        for m in nj_matches:
            print(f"  {m.date} | {m.home_team.name} {m.home_score} x {m.away_score} {m.away_team.name} | Status: {m.status}")
            
    except Exception as e:
        print(f"Erro na Austrália: {e}")

    # Áustria (ID 44)
    try:
        l_aut = League.objects.get(id=44)
        m_aut = Match.objects.filter(league=l_aut).count()
        print(f"\nÁustria (ID 44): {m_aut} jogos")
    except Exception as e:
        print(f"Erro na Áustria: {e}")

if __name__ == '__main__':
    check_prod_data()
