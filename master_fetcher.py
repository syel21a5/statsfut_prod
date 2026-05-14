import json
import time
import argparse
import sys
from datetime import datetime, timedelta
from curl_cffi import requests

# Configurações das Ligas
LEAGUES = [
    {"id": 38, "season": 77040, "name": "Pro League", "country": "Belgica", "year": 2026},
    {"id": 34, "season": 77356, "name": "Ligue 1", "country": "Franca", "year": 2026},
    {"id": 35, "season": 77333, "name": "Bundesliga", "country": "Alemanha", "year": 2026},
    {"id": 215, "season": 77152, "name": "Super League", "country": "Suica", "year": 2026},
    {"id": 155, "season": 87913, "name": "Liga Profesional", "country": "Argentina", "year": 2026},
    {"id": 420, "season": 78592, "name": "A-League Men", "country": "Australia", "year": 2026},
    {"id": 45, "season": 77382, "name": "Bundesliga", "country": "Austria", "year": 2026},
    {"id": 325, "season": 87678, "name": "Brasileirão", "country": "Brasil", "year": 2026},
]

def fetch_api(session, url, sleep_time=0.5):
    try:
        time.sleep(sleep_time)
        response = session.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Erro ao acessar {url}: {e}")
        return None

def should_update(session, t_id, s_id):
    """Verifica se existem jogos hoje, ontem ou nos próximos dias, incluindo sub-torneios (Playoffs)."""
    # 1. Obter Standings para descobrir sub-torneios (ex: Austria Championship Round)
    st_url = f"https://api.sofascore.com/api/v1/unique-tournament/{t_id}/season/{s_id}/standings/total"
    st_data = fetch_api(session, st_url)
    
    tournaments = [(t_id, True)] # (id, is_unique)
    if st_data and 'standings' in st_data:
        for group in st_data['standings']:
            sub_id = group.get('tournament', {}).get('id')
            if sub_id and sub_id != t_id:
                if not any(t[0] == sub_id for t in tournaments):
                    tournaments.append((sub_id, False))
    
    now = datetime.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    # Aumentado para 10 dias para garantir captura de hiatos em playoffs
    relevant_dates = [yesterday, today] + [today + timedelta(days=i) for i in range(1, 11)]
    
    for tid, is_unique in tournaments:
        prefix = "unique-tournament" if is_unique else "tournament"
        
        # Pegar a rodada atual do torneio específico
        r_url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/rounds"
        r_data = fetch_api(session, r_url)
        if not r_data: continue
        
        current_round = r_data.get('currentRound', {}).get('round', 1)
        
        # Pegar eventos da rodada atual
        e_url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/events/round/{current_round}"
        data_events = fetch_api(session, e_url)
        if not data_events: 
            print(f"AVISO: Falha ao buscar eventos para {tid} rodada {current_round}")
            continue
        
        for event in data_events.get('events', []):
            ts = event.get('startTimestamp')
            if ts:
                dt = datetime.fromtimestamp(ts).date()
                if dt in relevant_dates:
                    status = event.get('status', {}).get('type')
                    if status != 'finished' or dt >= yesterday:
                        return True
    
    return False

def scrape_league(session, t_id, s_id, last_rounds=None):
    payload = {
        "tournament_id": t_id,
        "season_id": s_id,
        "standings": None,
        "rounds": []
    }
    
    # 1. Standings
    st_url = f"https://api.sofascore.com/api/v1/unique-tournament/{t_id}/season/{s_id}/standings/total"
    st_data = fetch_api(session, st_url)
    if st_data: payload['standings'] = st_data
    
    # 2. Descobrir torneios extras (Playoffs, etc)
    tournaments = [(t_id, "Regular Season", True)]
    if st_data and 'standings' in st_data:
        for group in st_data['standings']:
            sub_id = group.get('tournament', {}).get('id')
            if sub_id and sub_id != t_id:
                if not any(t[0] == sub_id for t in tournaments):
                    tournaments.append((sub_id, group.get('name', 'League'), False))
                    
    # 3. Rodadas
    for tid, label, is_unique in tournaments:
        prefix = "unique-tournament" if is_unique else "tournament"
        r_url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/rounds"
        r_data = fetch_api(session, r_url)
        if r_data and 'rounds' in r_data:
            all_r = r_data['rounds']
            if last_rounds:
                # Lógica Inteligente: Pegar a rodada atual e as adjacentes
                current_r = r_data.get('currentRound', {}).get('round', 1)
                # Queremos a anterior (para resultados), a atual e as próximas (para futuros)
                target_rounds = [current_r - 1, current_r, current_r + 1, current_r + 2]
                all_r = [r for r in all_r if r['round'] in target_rounds]
                print(f"    - {label}: Processando rodadas {target_rounds}")
            
            for r_info in all_r:
                r_num = r_info['round']
                e_url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/events/round/{r_num}"
                e_data = fetch_api(session, e_url)
                if e_data:
                    payload['rounds'].append({
                        "round_label": label,
                        "round_number": r_num,
                        "events": e_data.get('events', [])
                    })
    return payload

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full-scan', action='store_true')
    parser.add_argument('--tor', action='store_true', help='Usar proxy Tor (127.0.0.1:9050 ou 9150)')
    args = parser.parse_args()
    
    session = requests.Session(impersonate="chrome120")
    
    if args.tor:
        # Tenta 9050 (Docker/Linux) ou 9150 (Windows Tor Browser)
        proxies = {"http": "socks5://127.0.0.1:9050", "https": "socks5://127.0.0.1:9050"}
        try:
            session.get("https://api.sofascore.com/api/v1/unique-tournament/35/season/52331/standings/total", proxies=proxies, timeout=5)
            session.proxies = proxies
            print("🌐 Usando Tor (Porta 9050)")
        except:
            proxies = {"http": "socks5://127.0.0.1:9150", "https": "socks5://127.0.0.1:9150"}
            session.proxies = proxies
            print("🌐 Usando Tor (Porta 9150)")

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    })
    
    updated_leagues = []
    
    for league in LEAGUES:
        name = f"{league['country']} - {league['name']}"
        print(f"\nAnalizando {name}...")
        
        force = args.full_scan
        if force or should_update(session, league['id'], league['season']):
            print(f"  >>> Jogos detectados ou Force Scan. Atualizando...")
            # No modo inteligente, pegamos apenas as 2 últimas rodadas
            # No modo Full Scan, pegamos tudo.
            limit = None if force else 2
            payload = scrape_league(session, league['id'], league['season'], last_rounds=limit)
            
            filename = f"payload_{league['country'].lower()}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False)
            
            updated_leagues.append(league)
        else:
            print(f"  --- Sem jogos recentes. Pulando para economizar minutos.")
            
    # Gera um arquivo de controle para o GitHub Actions saber o que processar
    with open('updated_leagues.json', 'w', encoding='utf-8') as f:
        json.dump(updated_leagues, f, ensure_ascii=False)
    
    print(f"\n✅ Concluído! {len(updated_leagues)} ligas atualizadas.")

if __name__ == "__main__":
    main()
