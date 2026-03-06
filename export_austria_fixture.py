import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.serializers import serialize
from matches.models import League, Team, Match, Season, LeagueStanding

def export_austria_fixture():
    print("Buscando a liga da Áustria...")
    league = League.objects.filter(country='Austria').first()
    if not league:
        print("Liga da Áustria não encontrada.")
        return

    print(f"Liga encontrada: {league.name} (ID: {league.id})")

    # Get all related objects
    teams = Team.objects.filter(league=league)
    matches = Match.objects.filter(league=league)
    standings = LeagueStanding.objects.filter(league=league)
    season_ids = list(matches.values_list('season_id', flat=True).distinct())
    seasons = Season.objects.filter(id__in=season_ids)

    all_objects = list(league.__class__.objects.filter(id=league.id))
    all_objects += list(seasons)
    all_objects += list(teams)
    all_objects += list(matches)
    all_objects += list(standings)

    print(f"Exportando:")
    print(f"  - 1 liga")
    print(f"  - {seasons.count()} temporadas")
    print(f"  - {teams.count()} times")
    print(f"  - {matches.count()} partidas")
    print(f"  - {standings.count()} posições na tabela")

    # Write to fixture
    fixture_data = json.loads(serialize('json', all_objects))
    output_path = 'austria_fixture.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(fixture_data, f, ensure_ascii=False, indent=2)

    import os
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nFixture salvo em '{output_path}' ({size_mb:.2f} MB)")
    print("Pronto para enviar ao servidor!")

if __name__ == '__main__':
    export_austria_fixture()
