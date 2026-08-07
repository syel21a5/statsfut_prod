import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match

def check_austria():
    print("Verificando dados da Liga da Áustria...")
    league = League.objects.filter(country='Austria').first()
    if not league:
        print("Liga não encontrada!")
        return
        
    teams = Team.objects.filter(league=league)
    matches = Match.objects.filter(league=league)
    
    print(f"Liga: {league.name} (ID: {league.id})")
    print(f"Total de Times: {teams.count()}")
    print(f"Total de Partidas: {matches.count()}")
    
    print("\nÚltimos 5 jogos finalizados:")
    for m in matches.filter(status='Finished').order_by('-date')[:5]:
        print(f"[{m.date.strftime('%d/%m/%Y')}] {m.home_team.name} {m.home_score} x {m.away_score} {m.away_team.name}")

if __name__ == '__main__':
    check_austria()
