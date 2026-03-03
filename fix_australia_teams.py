import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, LeagueStanding

def merge_teams(correct_name, wrong_names):
    correct_team = Team.objects.filter(name=correct_name).first()
    if not correct_team:
        print(f"Time correto não encontrado: {correct_name}")
        return

    for wrong_name in wrong_names:
        wrong_team = Team.objects.filter(name=wrong_name).first()
        if not wrong_team:
            continue
            
        print(f"Mesclando: {wrong_name} -> {correct_name}")
        
        # Move jogos
        Match.objects.filter(home_team=wrong_team).update(home_team=correct_team)
        Match.objects.filter(away_team=wrong_team).update(away_team=correct_team)
        
        # Remove standings do errado
        LeagueStanding.objects.filter(team=wrong_team).delete()
        
        # Deleta o time errado
        wrong_team.delete()

def fix_australian_teams():
    print("=== Consertando Nomes Duplicados da Austrália ===")
    
    # Mapeamento do nome Certo (como o sistema import_odds vai preferir e o mais completo) 
    # -> e da lista de nomes errados que os scrapers antigos criaram.
    merges = {
        'Adelaide United': ['Adelaide Utd'],
        'Central Coast Mariners': ['Central Coast'],
        'Melbourne Victory': ['Melbourne V.', 'Melbourne V'],
        'Newcastle Jets FC': ['Newcastle Jets'],
        'Western Sydney Wanderers': ['Western Sydney', 'WS Wanderers'],
        'Auckland FC': ['Auckland'],
        'Wellington Phoenix FC': ['Wellington Phoenix', 'Wellington'],
    }
    
    for correct, wrongs in merges.items():
        merge_teams(correct, wrongs)
        
    print("\nExecutando recálculo da tabela da Austrália após fundir os times...")
    from django.core.management import call_command
    # Usaremos --all para garantir que pegamos exatamente a liga certa
    call_command('recalculate_standings', '--all')
    print("Sucesso!")

if __name__ == '__main__':
    fix_australian_teams()
