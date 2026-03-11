import os
import django
import sys
from django.db import transaction

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League, Match, LeagueStanding

def ultimate_fix():
    league = League.objects.filter(name__iexact='Ligue 1', country__iexact='Franca').first()
    if not league:
       for c in ['França', 'France']:
           league = League.objects.filter(name__iexact='Ligue 1', country__iexact=c).first()
           if league: break

    if not league:
        print("Liga Ligue 1 não encontrada.")
        return

    # 1. Mapeamento definitivo de IDs
    standard_teams = {
        'Brest': '1715',
        'Marseille': '1641',
        'Lens': '1648',
        'Monaco': '1653',
        'Toulouse': '1681',
        'PSG': '1644',
        'Auxerre': '1646',
        'Rennes': '1658',
        'Nantes': '1647',
        'Le Havre': '1662',
        'Nice': '1661',
        'Lorient': '1656',
        'Angers': '1684',
        'Lille': '1643',
        'Strasbourg': '1659',
        'Lyon': '1649',
        'Reims': '1682',
        'Montpellier': '1642',
        'Paris FC': '6070',
        'Metz': '1651'
    }

    print("\n=== 1. Limpeza de API IDs (Evitar Constraints) ===")
    Team.objects.filter(league=league).update(api_id=None)

    print("\n=== 2. Garantindo criação dos 18 times base ===")
    for name in standard_teams.keys():
        Team.objects.get_or_create(name=name, league=league)

    print("\n=== 3. Fundindo Times Duplicados / Fantasmas ===")
    valid_names = list(standard_teams.keys())
    
    # Recarregar
    all_teams = list(Team.objects.filter(league=league))

    with transaction.atomic():
        for wrong_team in all_teams:
            if wrong_team.name not in valid_names:
                correct_name = None
                n_lower = wrong_team.name.lower()
                
                if 'paris' in n_lower and 'germain' in n_lower: correct_name = 'PSG'
                elif 'monaco' in n_lower: correct_name = 'Monaco'
                elif 'brest' in n_lower: correct_name = 'Brest'
                elif 'strasbourg' in n_lower: correct_name = 'Strasbourg'
                elif 'lyon' in n_lower: correct_name = 'Lyon'
                elif 'marseille' in n_lower: correct_name = 'Marseille'
                elif 'rennes' in n_lower: correct_name = 'Rennes'
                elif 'lens' in n_lower: correct_name = 'Lens'
                elif 'reims' in n_lower: correct_name = 'Reims'
                elif 'toulouse' in n_lower: correct_name = 'Toulouse'
                
                if correct_name:
                    correct_team = Team.objects.get(name=correct_name, league=league)
                    print(f"-> Fusão: {wrong_team.name} vai virar {correct_team.name}...")
                    
                    # Move matches
                    Match.objects.filter(home_team=wrong_team).update(home_team=correct_team)
                    Match.objects.filter(away_team=wrong_team).update(away_team=correct_team)
                    
                    # Delete wrong entries
                    LeagueStanding.objects.filter(team=wrong_team).delete()
                    wrong_team.delete()
                else:
                    print(f"AVISO: Time estranho encontrado não mapeado para deleção: {wrong_team.name}")

    print("\n=== 4. Re-aplicando IDs de modo seguro ===")
    for name, sofa_id in standard_teams.items():
        sofa_api_id = f"sofa_{sofa_id}"
        Team.objects.filter(name=name, league=league).update(api_id=sofa_api_id)
        print(f"Logo OK: {name} -> {sofa_api_id}")

if __name__ == "__main__":
    ultimate_fix()
    print("\nSUCESSO TOTAL! Agora rode o recalculate_standings!")
