import json
import os
import django
import sys

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'statsfut.settings')
django.setup()

from matches.models import Match, Goal, Team, League

def run():
    file_path = 'argentina_data.json'
    if not os.path.exists(file_path):
        print(f"Erro: Arquivo {file_path} não encontrado.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Iniciando importação de {len(data)} partidas...")
    
    updated = 0
    goals_total = 0
    
    for item in data:
        match = Match.objects.filter(api_id=item['api_id']).first()
        if match:
            # Update stats
            match.home_corners, match.away_corners = item['corners']
            match.home_yellow, match.away_yellow = item['yellow']
            match.home_red, match.away_red = item['red']
            match.home_shots, match.away_shots = item['shots']
            match.home_shots_on_target, match.away_shots_on_target = item['shots_on_target']
            match.home_fouls, match.away_fouls = item['fouls']
            match.save()
            
            # Update goals
            if item['goals']:
                Goal.objects.filter(match=match).delete()
                for g_data in item['goals']:
                    team = Team.objects.filter(name=g_data['team'], league=match.league).first()
                    if team:
                        Goal.objects.create(
                            match=match,
                            team=team,
                            player_name=g_data['player'],
                            minute=g_data['min'],
                            is_own_goal=g_data['own'],
                            is_penalty=g_data['pen']
                        )
                        goals_total += 1
            
            updated += 1
            if updated % 100 == 0:
                print(f"Progresso: {updated} partidas processadas...")

    print(f"✅ Sucesso! {updated} partidas atualizadas com estatísticas e {goals_total} gols importados.")

if __name__ == "__main__":
    run()
