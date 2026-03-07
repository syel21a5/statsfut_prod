import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, League, Season

def diag_austr():
    print("--- Diagnóstico de Season e Matches na Produção ---")
    try:
        league = League.objects.get(id=21)
    except:
        print("Erro: Liga 21 não existe.")
        return

    for s in Season.objects.all():
        m_count = Match.objects.filter(league=league, season=s).count()
        print(f"Season ID: {s.id} | Year: {s.year} | Jogos Austrália: {m_count}")

    # Checar se existem jogos da Liga 21 sem Season
    none_season = Match.objects.filter(league=league, season__isnull=True).count()
    print(f"Jogos Austrália SEM Season: {none_season}")
    
    # Checar datas dos jogos
    latest = Match.objects.filter(league=league).order_by('-date')[:3]
    print("\nÚltimos jogos no DB:")
    for m in latest:
        print(f"ID: {m.id} | Date: {m.date} | {m.home_team.name} x {m.away_team.name} | Status: {m.status}")

if __name__ == '__main__':
    diag_austr()
