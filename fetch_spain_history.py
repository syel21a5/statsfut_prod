import os
import time
import json
import argparse
from curl_cffi import requests

def fetch_api(session, url, sleep_time=0.7):
    try:
        time.sleep(sleep_time)
        response = session.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
        print(f"Erro na API {url}: Status {response.status_code}")
        return None
    except Exception as e:
        print(f"Exceção ao acessar {url}: {e}")
        return None

def fetch_season_data(session, tournament_id, season_id, year_label):
    print(f"\n🚀 Raspando Temporada {year_label} (Torneio {tournament_id}, Temporada {season_id})...")
    payload = {
        "tournament_id": tournament_id,
        "season_id": season_id,
        "standings": None,
        "rounds": []
    }

    # 1. Standings
    standings_url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{season_id}/standings/total"
    standings_data = fetch_api(session, standings_url)
    if standings_data:
        payload['standings'] = standings_data

    # 2. Torneios extras
    tournaments_to_scrape = [(tournament_id, "Regular Season", True)]
    if standings_data and 'standings' in standings_data:
        for group in standings_data['standings']:
            group_name = group.get('name', 'League')
            sub_id = group.get('tournament', {}).get('id')
            if sub_id and sub_id != tournament_id:
                if not any(t[0] == sub_id for t in tournaments_to_scrape):
                    tournaments_to_scrape.append((sub_id, group_name, False))

    # 3. Rodadas
    for t_id, label, is_unique in tournaments_to_scrape:
        print(f">>> Raspando {label}...")
        prefix = "unique-tournament" if is_unique else "tournament"
        rounds_url = f"https://api.sofascore.com/api/v1/{prefix}/{t_id}/season/{season_id}/rounds"
        rounds_data = fetch_api(session, rounds_url)
        
        if rounds_data and 'rounds' in rounds_data:
            all_rounds = rounds_data['rounds']
            for round_info in all_rounds:
                round_num = round_info['round']
                print(f"Buscando {label} - Rodada {round_num}...", end='\r')
                events_url = f"https://api.sofascore.com/api/v1/{prefix}/{t_id}/season/{season_id}/events/round/{round_num}"
                events_data = fetch_api(session, events_url)
                if events_data:
                    payload['rounds'].append({
                        "round_label": label,
                        "round_number": round_num,
                        "events": events_data.get('events', [])
                    })
            print(f"\n{label} finalizado. {len(all_rounds)} rodadas.")

    if not payload['rounds']:
        print("❌ Nenhuma rodada coletada!")
        return False

    os.makedirs(f"historical_data/Spain/LaLiga", exist_ok=True)
    with open(f"historical_data/Spain/LaLiga/{year_label}.json", 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ Sucesso! {year_label}.json salvo.")
    return True

def main():
    parser = argparse.ArgumentParser(description="Busca histórico da La Liga (Espanha) no SofaScore")
    parser.add_argument('--start', type=int, default=2020, help="Ano inicial")
    parser.add_argument('--end', type=int, default=2025, help="Ano final")
    args = parser.parse_args()

    session = requests.Session(impersonate="chrome120")
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    })

    TOURNAMENT_ID = 8
    
    # IDs das temporadas da La Liga
    SEASONS_MAP = {
        2025: 61643, # 2024/2025
        2024: 52376, # 2023/2024
        2023: 42409, # 2022/2023
        2022: 37223, # 2021/2022
        2021: 32501, # 2020/2021
        2020: 24127, # 2019/2020
    }

    for year in range(args.start, args.end + 1):
        if year in SEASONS_MAP:
            season_id = SEASONS_MAP[year]
            fetch_season_data(session, TOURNAMENT_ID, season_id, year)
        else:
            print(f"Temporada {year} não mapeada.")

if __name__ == "__main__":
    main()
