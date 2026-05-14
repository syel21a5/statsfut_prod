import time
import random
from curl_cffi import requests
import os
import django
import sys

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match, Goal, League

def run():
    league = League.objects.get(id=22) # Argentina
    # Busca partidas que tenham gols no placar mas 0 gols no banco detalhado
    matches = []
    all_matches = Match.objects.filter(league=league, home_corners__isnull=False)
    
    for m in all_matches:
        total_score = (m.home_score or 0) + (m.away_score or 0)
        if total_score > 0 and m.goals.count() == 0:
            matches.append(m)

    total = len(matches)
    if total == 0:
        print("✅ Nenhum gol precisando de reparo. Todos os jogos com placar já possuem gols detalhados.")
        return

    print(f"🛠️ Iniciando reparo de gols para {total} partidas da Argentina...")
    
    # Configura sessão com Tor (Porta 9150 do Tor Browser no Windows)
    session = requests.Session(impersonate="chrome120")
    session.proxies = {"http": "socks5://127.0.0.1:9150", "https": "socks5://127.0.0.1:9150"}
    
    updated = 0
    for idx, match in enumerate(matches, 1):
        sofa_id = match.api_id.replace('sofa_', '')
        print(f"[{idx}/{total}] Reparando gols: {match.home_team} {match.home_score}x{match.away_score} {match.away_team}")
        
        url = f"https://api.sofascore.com/api/v1/event/{sofa_id}/incidents"
        try:
            time.sleep(random.uniform(2, 4)) # Delay curto
            resp = session.get(url, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if 'incidents' in data:
                    goals_list = [i for i in data['incidents'] if i.get('incidentType') == 'goal']
                    for gol in goals_list:
                        minute = gol.get('time')
                        extra = gol.get('addedTime', 0)
                        total_min = minute + (extra or 0)
                        player_name = gol.get('player', {}).get('name', 'Unknown Player')
                        is_home = gol.get('isHome')
                        team = match.home_team if is_home else match.away_team
                        
                        Goal.objects.create(
                            match=match,
                            team=team,
                            player_name=player_name,
                            minute=total_min,
                            is_own_goal=(gol.get('incidentType') == 'ownGoal'),
                            is_penalty=(gol.get('incidentType') == 'penalty')
                        )
                    updated += 1
            elif resp.status_code == 403:
                print("🛑 Bloqueado pelo Tor. Troque a identidade no Tor Browser e tente de novo.")
                break
        except Exception as e:
            print(f"Erro no jogo {sofa_id}: {e}")

    print(f"✅ Concluído! {updated} partidas tiveram seus gols restaurados.")

if __name__ == "__main__":
    run()
