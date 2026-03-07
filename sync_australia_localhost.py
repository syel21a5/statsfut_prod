import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, League

def sync_local():
    print("--- Sincronização Local da Austrália ---")
    
    # 1. Identificar a Liga Local (ID 9 no localhost)
    try:
        local_league = League.objects.get(id=9)
        print(f"Liga Local: {local_league.name} (ID: 9)")
    except League.DoesNotExist:
        print("Erro: Liga ID 9 não encontrada no seu localhost!")
        return

    master_teams = {
        "sofa_2934": "Newcastle Jets FC",
        "sofa_800224": "Auckland FC",
        "sofa_5971": "Sydney FC",
        "sofa_2946": "Adelaide United",
        "sofa_5970": "Melbourne Victory",
        "sofa_5966": "Central Coast Mariners",
        "sofa_371682": "Macarthur FC",
        "sofa_72926": "Western Sydney Wanderers",
        "sofa_5968": "Brisbane Roar",
        "sofa_42210": "Melbourne City",
        "sofa_2945": "Perth Glory",
        "sofa_7568": "Wellington Phoenix",
        "sofa_342935": "Western United"
    }

    print("\nLimpando duplicatas e unificando nomes no seu localhost...")
    for api_id, clean_name in master_teams.items():
        teams_to_fix = Team.objects.filter(league=local_league).filter(
            django.db.models.Q(api_id=api_id) | 
            django.db.models.Q(name__icontains=clean_name.split()[0])
        )
        
        if teams_to_fix.exists():
            primary_team = teams_to_fix.first()
            primary_team.name = clean_name
            primary_team.api_id = api_id
            primary_team.save()
            
            for other in teams_to_fix.exclude(id=primary_team.id):
                print(f"  Mesclando duplicata: {other.name} (ID {other.id}) -> {clean_name}")
                Match.objects.filter(home_team=other).update(home_team=primary_team)
                Match.objects.filter(away_team=other).update(away_team=primary_team)
                other.delete()
        else:
            Team.objects.create(name=clean_name, api_id=api_id, league=local_league)
            print(f"  Criado time: {clean_name}")

    print("\nSINCRONIZAÇÃO COMPLETA!")

if __name__ == '__main__':
    sync_local()
