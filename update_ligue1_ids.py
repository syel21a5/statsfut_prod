import os
import django
import sys

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League

def update_ids():
    try:
        league = League.objects.get(name='Ligue 1')
    except League.DoesNotExist:
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
        'RC Strasbourg': '1659',
        'Lyon': '1649',
        'Reims': '1682',
        'Montpellier': '1642',
        'Paris FC': '6070',
        'Metz': '1651'
    }

    # Limpar IDs para evitar IntegrityError durante a transição
    Team.objects.filter(league=league).update(api_id=None)
    print("IDs limpos para Ligue 1.")

    for name, s_id in mapping.items():
        sofa_api_id = f"sofa_{s_id}"
        # Se houver mais de um time com nomes similares (ex: Strasbourg e RC Strasbourg),
        # mantemos apenas um para evitar erro de duplicata no api_id unique=True
        teams = Team.objects.filter(league=league, name__icontains=name)
        if teams.count() > 1:
            main_team = teams.first()
            # Deletamos os outros (ou poderíamos fazer merge, mas para logos o delete resolve o erro de ID)
            teams.exclude(id=main_team.id).delete()
            print(f"Duplicatas de {name} removidas.")
            main_team.api_id = sofa_api_id
            main_team.save()
        elif teams.exists():
            teams.update(api_id=sofa_api_id)
        
        print(f"Updated {name} to {sofa_api_id}")

if __name__ == "__main__":
    update_ids()
