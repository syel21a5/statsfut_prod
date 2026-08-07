import os
import json
import time
import random
from curl_cffi import requests

def fetch_api(url, sleep_range=(3.0, 6.0)):
    delay = random.uniform(*sleep_range)
    time.sleep(delay)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Origin': 'https://www.sofascore.com',
        'Referer': 'https://www.sofascore.com/'
    }
    
    # Tentativas: direto primeiro, depois via Tor proxy se falhar
    for attempt in range(2):
        try:
            proxies = None
            if attempt > 0:
                print("    (Tentando via proxy do Tor...)")
                proxies = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
            
            response = requests.get(url, headers=headers, proxies=proxies, impersonate="chrome110", timeout=20)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"    Erro 404 na URL: {url} (endpoint indisponível)")
                return None
            print(f"    Erro {response.status_code} na tentativa {attempt+1} para a URL: {url}")
        except Exception as e:
            print(f"    Exceção {e} na tentativa {attempt+1} para a URL: {url}")
        time.sleep(random.uniform(2, 4))
    return None

def fetch_sudamericana_history():
    base_dir = "historical_data/America do Sul/Copa Sul-Americana"
    os.makedirs(base_dir, exist_ok=True)
    
    # Mapeamento de Ano para Season ID da Copa Sul-Americana
    seasons = {
        2026: 87770,
        2025: 70070,
        2024: 57297,
        2023: 47968,
        2022: 40175,
        2021: 35645,
        2020: 26788
    }
    
    tournament_id = 480
    
    for year, s_id in seasons.items():
        print(f"\n>>> Coletando temporada {year} (ID: {s_id}) da Sudamericana...")
        payload = {"rounds": [], "standings": None}
        
        # 1. Obter a classificação (standings)
        print("  Baixando classificação (standings)...")
        st_url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{s_id}/standings/total"
        standings_data = fetch_api(st_url)
        if standings_data:
            payload['standings'] = standings_data
            print("  ✅ Classificação obtida com sucesso.")
        else:
            print("  ⚠️ Classificação não disponível ou falhou.")
        
        # 2. Obter a lista de rounds
        url_rounds = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{s_id}/rounds"
        rounds_data = fetch_api(url_rounds)
        
        if rounds_data and 'rounds' in rounds_data:
            print(f"  Encontrados {len(rounds_data['rounds'])} rounds para a temporada {year}.")
            for rnd in rounds_data['rounds']:
                r_num = rnd.get('round')
                r_prefix = rnd.get('prefix')
                label = f"{r_prefix}{r_num}" if r_prefix else str(r_num)
                
                url_events = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{s_id}/events/round/{r_num}"
                print(f"    Baixando rodada {label}...")
                events_data = fetch_api(url_events)
                
                if events_data and 'events' in events_data:
                    payload['rounds'].append({
                        "round_label": label,
                        "round_number": r_num,
                        "events": events_data['events']
                    })
        else:
            # Fallback paginado
            print("  Sem endpoint /rounds. Usando fallback paginado...")
            all_events = []
            for page in range(10):
                url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{s_id}/events/last/{page}"
                data = fetch_api(url)
                if not data or not data.get('events'):
                    break
                all_events.extend(data['events'])
                if not data.get('hasNextPage'):
                    break
            for page in range(5):
                url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{s_id}/events/next/{page}"
                data = fetch_api(url)
                if not data or not data.get('events'):
                    break
                all_events.extend(data['events'])
                if not data.get('hasNextPage'):
                    break
                    
            if all_events:
                rounds_map = {}
                for ev in all_events:
                    r_num = ev.get('roundInfo', {}).get('round', 1) if ev.get('roundInfo') else 1
                    rounds_map.setdefault(r_num, []).append(ev)
                for r_num in sorted(rounds_map.keys()):
                    payload['rounds'].append({
                        "round_label": str(r_num),
                        "round_number": r_num,
                        "events": rounds_map[r_num]
                    })
                print(f"  ✅ Fallback coletou {len(all_events)} eventos.")
        
        if payload['rounds'] or payload['standings']:
            filename = f"{base_dir}/{year}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f"  ✅ Salvo em {filename} (Rounds: {len(payload['rounds'])})")
        else:
            print(f"  ❌ Nenhum dado coletado para {year}")

if __name__ == "__main__":
    fetch_sudamericana_history()
