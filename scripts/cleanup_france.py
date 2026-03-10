import os
import django
import sys

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match, LeagueStanding

def cleanup():
    print("🚀 Iniciando limpeza de dados intrusos na França...")
    
    try:
        france_league = League.objects.get(name='Ligue 1', country='Franca')
    except League.DoesNotExist:
        print("❌ Liga da França não encontrada.")
        return

    # Lista de times tunisianos identificados (e outros possíveis intrusos)
    intruder_names = [
        'ES Tunis', 'Club Africain', 'ES Zarzis', 'AS Soliman', 'AS New Soger', 
        'Douanes', 'Jeunesse Sportive Omrane', 'Malole', 'Mouna', 'Ouakam', 
        'Panda B5', 'RCK', 'Réal du Faso', 'Salitas', 'Simba', 'Sonacos', 
        'US Monastirienne', 'US Tchologo', 'Metz' # Metz caiu, mas se estiver com 0 jogos pode ser sobra
    ]
    
    # Times que SABEMOS que são da Ligue 1 França 2025/26 (18 times)
    official_france_2026 = [
        'Angers', 'Auxerre', 'Brest', 'Le Havre', 'Lens', 'Lille', 'Lorient', 
        'Lyon', 'Marseille', 'Monaco', 'Montpellier', 'Nantes', 'Nice', 
        'PSG', 'Reims', 'Rennes', 'Saint-Etienne', 'Strasbourg', 'Toulouse'
    ]

    # 1. Identificar times intrusos vinculados à liga da França
    intruders = Team.objects.filter(league=france_league).exclude(name__in=official_france_2026)
    
    print(f"🔍 Encontrados {intruders.count()} times intrusos.")
    
    for team in intruders:
        print(f"  🗑️ Removendo: {team.name}")
        # Remover partidas vinculadas
        matches_deleted = Match.objects.filter(django.db.models.Q(home_team=team) | django.db.models.Q(away_team=team)).delete()
        # Remover standings
        standings_deleted = LeagueStanding.objects.filter(team=team).delete()
        # Remover o time
        team.delete()

    print("✅ Limpeza concluída! Recalculando tabela...")
    
    from django.core.management import call_command
    call_command('recalculate_standings', league_name='Ligue 1', country='Franca')

if __name__ == "__main__":
    cleanup()
