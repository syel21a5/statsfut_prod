import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, League

def check_matches():
    print("--- Analisando Jogos da Austrália na Produção ---")
    matches = Match.objects.filter(league_id=21).order_by('-date')
    
    print(f"Total de jogos salvos: {matches.count()}")
    
    status_counts = {}
    for m in matches:
        status_counts[m.status] = status_counts.get(m.status, 0) + 1
    
    print("\nResumo por Status:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
        
    print("\nJogos que deveriam estar na tabela mas talvez não estejam (Newcastle Jets FC):")
    nj_team = Team.objects.get(name="Newcastle Jets FC", league_id=21)
    nj_matches = Match.objects.filter(Q(home_team=nj_team) | Q(away_team=nj_team)).order_by('-date')
    
    for m in nj_matches:
        has_score = (m.home_score is not None and m.away_score is not None)
        print(f"ID: {m.id} | Date: {m.date} | {m.home_team.name} {m.home_score} x {m.away_score} {m.away_team.name} | Status: {m.status} | Tem Placar? {has_score}")

if __name__ == '__main__':
    from django.db.models import Q
    check_matches()
