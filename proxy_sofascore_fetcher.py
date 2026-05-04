import json
import time
import argparse
from curl_cffi import requests

def fetch_api(session, url, sleep_time=0.7):
    try:
        time.sleep(sleep_time)  # Rate limiting otimizado
        response = session.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro na API {url}: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"Exceção ao acessar {url}: {e}")
        return None

def fetch_seasons(session, tournament_id):
    url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/seasons"
    data = fetch_api(session, url)
    if not data:
        return []
    seasons = data.get("seasons", [])
    def to_int(v):
        try:
            return int(v)
        except Exception:
            return 0
    seasons_sorted = sorted(seasons, key=lambda s: to_int(s.get("year")), reverse=True)
    return seasons_sorted

def main():
    parser = argparse.ArgumentParser(description="Busca payloads do SofaScore de forma otimizada")
    parser.add_argument('--tournament', type=int, required=True, help="ID do Torneio")
    parser.add_argument('--season', type=int, required=False, help="ID da Temporada")
    parser.add_argument('--list-seasons', action='store_true', help="Lista Season IDs")
    parser.add_argument('--last-rounds', type=int, default=None, help="Limitar busca às últimas X rodadas (economiza muitos minutos)")
    args = parser.parse_args()

    session = requests.Session(impersonate="chrome120")
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    })

    if args.list_seasons:
        seasons = fetch_seasons(session, args.tournament)
        if not seasons: return
        print(json.dumps(seasons, indent=2, ensure_ascii=False))
        return

    if not args.season:
        raise SystemExit("Forneça --season ou --list-seasons.")

    print(f"Raspagem OTIMIZADA para Torneio {args.tournament}, Temporada {args.season}...")

    payload = {
        "tournament_id": args.tournament,
        "season_id": args.season,
        "standings": None,
        "rounds": []
    }

    # 1. Standings
    standings_url = f"https://api.sofascore.com/api/v1/unique-tournament/{args.tournament}/season/{args.season}/standings/total"
    standings_data = fetch_api(session, standings_url)
    if standings_data:
        payload['standings'] = standings_data

    # 2. Torneios extras
    tournaments_to_scrape = [(args.tournament, "Regular Season", True)]
    if standings_data and 'standings' in standings_data:
        for group in standings_data['standings']:
            group_name = group.get('name', 'League')
            sub_id = group.get('tournament', {}).get('id')
            if sub_id and sub_id != args.tournament:
                if not any(t[0] == sub_id for t in tournaments_to_scrape):
                    tournaments_to_scrape.append((sub_id, group_name, False))

    # 3. Rodadas
    for t_id, label, is_unique in tournaments_to_scrape:
        print(f"\n>>> Raspando {label}...")
        prefix = "unique-tournament" if is_unique else "tournament"
        rounds_url = f"https://api.sofascore.com/api/v1/{prefix}/{t_id}/season/{args.season}/rounds"
        rounds_data = fetch_api(session, rounds_url)
        
        if rounds_data and 'rounds' in rounds_data:
            all_rounds = rounds_data['rounds']
            
            # FILTRO DE RODADAS OTIMIZADO
            if args.last_rounds:
                # SofaScore costuma marcar a rodada atual ou podemos pegar as últimas X
                # Vamos pegar as X últimas rodadas que possuem ID (ordem cronológica)
                all_rounds = all_rounds[-args.last_rounds:]
                print(f"Filtrando apenas as últimas {len(all_rounds)} rodadas para economizar tempo.")

            for round_info in all_rounds:
                round_num = round_info['round']
                print(f"Buscando {label} - Rodada {round_num}...")
                events_url = f"https://api.sofascore.com/api/v1/{prefix}/{t_id}/season/{args.season}/events/round/{round_num}"
                events_data = fetch_api(session, events_url)
                if events_data:
                    payload['rounds'].append({
                        "round_label": label,
                        "round_number": round_num,
                        "events": events_data.get('events', [])
                    })

    if len(payload['rounds']) == 0:
        print("\n❌ ERRO: Nenhuma rodada coletada!")
        import sys
        sys.exit(1)

    with open('payload.json', 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ Sucesso! {len(payload['rounds'])} rodadas salvas.")

if __name__ == '__main__':
    main()

if __name__ == '__main__':
    main()
