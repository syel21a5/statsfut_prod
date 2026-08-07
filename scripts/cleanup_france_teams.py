import os
import django
import sys

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League, Match, LeagueStanding
from django.db import transaction

def cleanup_teams():
    league = League.objects.filter(name__iexact='Ligue 1', country__iexact='Franca').first()
    if not league:
        for c in ['França', 'France']:
            league = League.objects.filter(name__iexact='Ligue 1', country__iexact=c).first()
            if league: break
            
    if not league:
        print("Liga Ligue 1 (Franca/França/France) não encontrada.")
        return

    # Mapeamento de Time Duplicado (Nome Errado -> Nome Correto)
    duplicates = {
        'Paris Saint-Germain FC': 'PSG',
        'AS Monaco FC': 'Monaco',
        'Stade Brestois 29': 'Brest',
        'Paris Saint-Germain': 'PSG',
        'AS Monaco': 'Monaco',
        'Stade Brestois': 'Brest',
    }

    with transaction.atomic():
        for wrong_name, correct_name in duplicates.items():
            try:
                correct_team = Team.objects.get(name=correct_name, league=league)
                wrong_teams = Team.objects.filter(name=wrong_name, league=league).exclude(id=correct_team.id)
                
                for wrong_team in wrong_teams:
                    print(f"Fundindo {wrong_team.name} (ID {wrong_team.id}) em {correct_team.name} (ID {correct_team.id})...")
                    
                    # 1. Mover Partidas
                    Match.objects.filter(home_team=wrong_team).update(home_team=correct_team)
                    Match.objects.filter(away_team=wrong_team).update(away_team=correct_team)
                    
                    # 2. Remover Standings do time errado
                    LeagueStanding.objects.filter(team=wrong_team).delete()
                    
                    # 3. Deletar time errado
                    wrong_team.delete()
                    print(f"Time {wrong_name} removido com sucesso.")
            
            except Team.DoesNotExist:
                print(f"Time correto {correct_name} não encontrado. Pulando...")
            except Exception as e:
                print(f"Erro ao processar {wrong_name}: {e}")

    print("\nLimpeza concluída. Recomendamos rodar o recalculate_standings agora.")

if __name__ == "__main__":
    cleanup_teams()
