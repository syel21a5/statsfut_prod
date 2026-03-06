import json
import time
import argparse
from curl_cffi import requests

def fetch_api(session, url):
    try:
        time.sleep(1.5)  # Rate limiting
        response = session.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro na API {url}: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"Exceção ao acessar {url}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Busca payloads do SofaScore e salva em payload.json")
    parser.add_argument('--tournament', type=int, required=True, help="ID do Torneio (ex: 136 para A-League)")
    parser.add_argument('--season', type=int, required=True, help="ID da Temporada (ex: 82603)")
    args = parser.parse_args()

    session = requests.Session(impersonate="chrome110")
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    })

    print(f"Iniciando raspagem crua para Torneio {args.tournament}, Temporada {args.season}...")

    payload = {
        "tournament_id": args.tournament,
        "season_id": args.season,
        "standings": None,
        "rounds": []
    }

    # 1. Obter Standings (contém lista de times formatados)
    standings_url = f"https://api.sofascore.com/api/v1/unique-tournament/{args.tournament}/season/{args.season}/standings/total"
    print(f"Buscando Standings...")
    standings_data = fetch_api(session, standings_url)
    if standings_data:
        payload['standings'] = standings_data

    # 2. Obter Rodadas
    rounds_url = f"https://api.sofascore.com/api/v1/unique-tournament/{args.tournament}/season/{args.season}/rounds"
    print(f"Buscando Rounds...")
    rounds_data = fetch_api(session, rounds_url)
    
    if rounds_data and 'rounds' in rounds_data:
        for round_info in rounds_data['rounds']:
            round_num = round_info['round']
            print(f"Buscando Eventos da Rodada {round_num}...")
            events_url = f"https://api.sofascore.com/api/v1/unique-tournament/{args.tournament}/season/{args.season}/events/round/{round_num}"
            events_data = fetch_api(session, events_url)
            if events_data:
                payload['rounds'].append({
                    "round_number": round_num,
                    "events": events_data.get('events', [])
                })

    print(f"Raspagem concluída. Salvando payload.json...")
    with open('payload.json', 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("payload.json gerado com sucesso!")

if __name__ == '__main__':
    main()
