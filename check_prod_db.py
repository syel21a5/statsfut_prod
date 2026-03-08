import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Match, Team, LeagueStanding

def check_db():
    print('\n--- VERIFICAÇÃO DO BANCO DE DADOS EM PRODUÇÃO ---')
    
    # Austria
    l_AT = League.objects.filter(country='Austria').first()
    if l_AT:
        m_AT = Match.objects.filter(league=l_AT).count()
        t_AT = Team.objects.filter(league=l_AT).count()
        s_AT = LeagueStanding.objects.filter(league=l_AT).count()
        print(f'🇦🇹 AUSTRIA: {m_AT} jogos | {t_AT} times | {s_AT} classificações salvas')
    else:
        print('AUSTRIA: Liga não encontrada ainda')
        
    # Australia
    l_AU = League.objects.filter(country='Australia').first()
    if l_AU:
        m_AU = Match.objects.filter(league=l_AU).count()
        t_AU = Team.objects.filter(league=l_AU).count()
        s_AU = LeagueStanding.objects.filter(league=l_AU).count()
        print(f'🇦🇺 AUSTRALIA: {m_AU} jogos | {t_AU} times | {s_AU} classificações salvas')
    else:
        print('AUSTRALIA: Liga não encontrada ainda')

if __name__ == '__main__':
    check_db()
