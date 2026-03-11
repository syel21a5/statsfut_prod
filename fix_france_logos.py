import os
import django
import sys
from django.db import transaction

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League, Match, LeagueStanding

def fix_all_france():
    league = League.objects.filter(name__iexact='Ligue 1', country__iexact='Franca').first()
    if not league:
        for c in ['França', 'France']:
            league = League.objects.filter(name__iexact='Ligue 1', country__iexact=c).first()
            if league: break

    if not league:
        print("Liga Ligue 1 não encontrada.")
        return

    mapping = {
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

    print("=== Corrigindo Logos (API IDs) ===")
    for db_name, sofa_id in mapping.items():
        sofa_api_id = f"sofa_{sofa_id}"
        team = Team.objects.filter(league=league, name__iexact=db_name).first()
        if team:
            try:
                if team.api_id != sofa_api_id:
                    Team.objects.filter(id=team.id).update(api_id=sofa_api_id)
                    print(f"Atualizado {team.name} para {sofa_api_id}")
            except Exception as e:
                print(f"Erro ao atualizar {team.name}: {e}")

    print("\n=== Corrigindo Strasbourg ===")
    with transaction.atomic():
        correct_team = Team.objects.filter(name__iexact='Strasbourg', league=league).first()
        wrong_team = Team.objects.filter(name__iexact='RC Strasbourg', league=league).first()

        if correct_team and wrong_team:
            print(f"Fundindo {wrong_team.name} em {correct_team.name}...")
            Match.objects.filter(home_team=wrong_team).update(home_team=correct_team)
            Match.objects.filter(away_team=wrong_team).update(away_team=correct_team)
            LeagueStanding.objects.filter(team=wrong_team).delete()
            wrong_team.delete()
            print("Duplicata RC Strasbourg removida e jogos mesclados com sucesso!")

if __name__ == "__main__":
    fix_all_france()
