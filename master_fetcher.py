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
    {"id": 136, "season": 82603, "name": "A-League Men", "country": "Australia", "year": 2026},
    {"id": 45, "season": 77382, "name": "Bundesliga", "country": "Austria", "year": 2026},
    {"id": 325, "season": 87678, "name": "Brasileirão", "country": "Brasil", "year": 2026},
    {"id": 39, "season": 76491, "name": "Superliga", "country": "Dinamarca", "year": 2026},
    {"id": 17, "season": 76986, "name": "Premier League", "country": "Inglaterra", "year": 2026},
    {"id": 8, "season": 77559, "name": "La Liga", "country": "Espanha", "year": 2026},
    {"id": 41, "season": 87930, "name": "Veikkausliiga", "country": "Finlandia", "year": 2026},
    {"id": 11653, "season": 88493, "name": "Primera Division", "country": "Chile", "year": 2026},
    {"id": 11620, "season": 87699, "name": "Liga MX", "country": "Mexico", "year": 2026},
    {"id": 242, "season": 86668, "name": "MLS", "country": "Estados Unidos", "year": 2026},
    {"id": 384, "season": 87760, "name": "Copa Libertadores", "country": "South America", "year": 2026},
    {"id": 480, "season": 87770, "name": "Copa Sul-Americana", "country": "South America", "year": 2026},
    # Ligas adicionadas recentemente ao automático
    {"id": 23, "season": 76457, "name": "Serie A", "country": "Italia", "year": 2026},
    {"id": 238, "season": 77806, "name": "Primeira Liga", "country": "Portugal", "year": 2026},
    {"id": 52, "season": 77805, "name": "Süper Lig", "country": "Turquia", "year": 2026},
    {"id": 37, "season": 77012, "name": "Eredivisie", "country": "Holanda", "year": 2026},
    {"id": 203, "season": 77142, "name": "Premier Liga", "country": "Russia", "year": 2026},
    {"id": 218, "season": 77625, "name": "Premier League", "country": "Ucrania", "year": 2026},
    {"id": 40, "season": 87925, "name": "Allsvenskan", "country": "Suecia", "year": 2026},
    {"id": 20, "season": 87809, "name": "Eliteserien", "country": "Noruega", "year": 2026},
    {"id": 202, "season": 76477, "name": "Ekstraklasa", "country": "Polonia", "year": 2026},
    {"id": 196, "season": 87931, "name": "J1 League", "country": "Japao", "year": 2026},
    {"id": 185, "season": 78175, "name": "Super League", "country": "Grecia", "year": 2026},
    {"id": 11539, "season": 88503, "name": "Primera A", "country": "Colombia", "year": 2026},
    {"id": 240, "season": 89674, "name": "Liga Pro", "country": "Equador", "year": 2026},
    {"id": 188, "season": 89094, "name": "Besta deild karla", "country": "Islandia", "year": 2026},
    {"id": 11540, "season": 87238, "name": "Primera Division", "country": "Paraguai", "year": 2026},
    {"id": 406, "season": 88529, "name": "Liga 1", "country": "Peru", "year": 2026},
    {"id": 36, "season": 77128, "name": "Premiership", "country": "Escocia", "year": 2026},
    {"id": 278, "season": 89288, "name": "Primera Division", "country": "Uruguai", "year": 2026},
]

def renew_tor_ip(session):
    """Solicita um novo circuito Tor (novo IP) via ControlPort 9051."""
    import socket
    try:
        # Pegar IP atual antes da troca
        try:
            r = session.get("https://api.ipify.org?format=json", timeout=10)
            old_ip = r.json().get("ip", "?")
        except:
            old_ip = "?"

        # Enviar NEWNYM para o Tor ControlPort
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 9051))
        s.send(b"AUTHENTICATE\r\n")
        resp = s.recv(256)
        if b"250" in resp:
            s.send(b"SIGNAL NEWNYM\r\n")
            resp = s.recv(256)
            if b"250" in resp:
                s.close()
                print(f"    ⏳ Aguardando 10s para o Tor construir novo circuito...")
                time.sleep(10)  # Tor precisa de 10s entre rotações

                # Pegar novo IP
                try:
                    r = session.get("https://api.ipify.org?format=json", timeout=10)
                    new_ip = r.json().get("ip", "?")
                except:
                    new_ip = "?"

                print(f"    🔄 IP Tor rotacionado: {old_ip} → {new_ip}")
                return True
        s.close()
    except Exception as e:
        print(f"    ⚠️ Falha ao rotacionar IP Tor: {e}")
    
    # Se falhou a rotação, pelo menos espera
    time.sleep(10)
    return False

def fetch_api(session, url, sleep_time=0.5, retries=3):
    for attempt in range(retries):
        try:
            time.sleep(sleep_time)
            response = session.get(url, timeout=15)
            if response.status_code == 200:
                return response.json()
            
            print(f"    ⚠️ Erro API {response.status_code} em {url} (Tentativa {attempt+1}/{retries})")
            if response.status_code in [403, 429, 503]:
                # Bloqueio ou congestionamento: tentar rotacionar IP do Tor
                if response.status_code == 403 and hasattr(session, 'proxies') and session.proxies:
                    print(f"    🛑 IP bloqueado pelo SofaScore! Solicitando novo IP...")
                    renew_tor_ip(session)
                else:
                    # Rate limit ou server error: espera progressiva
                    time.sleep(4 * (attempt + 1))
                continue
            
            # Se for 404, não adianta tentar de novo
            break
        except Exception as e:
            print(f"    ❌ Exceção ao acessar {url}: {e} (Tentativa {attempt+1}/{retries})")
            time.sleep(3)
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
    
    # 1b. Buscar sub-torneios de playoffs (cuptrees)
    ct_url = f"https://api.sofascore.com/api/v1/unique-tournament/{t_id}/season/{s_id}/cuptrees"
    ct_data = fetch_api(session, ct_url)
    if ct_data and 'cupTrees' in ct_data:
        for tree in ct_data['cupTrees']:
            sub_id = tree.get('tournament', {}).get('id')
            if sub_id and sub_id != t_id:
                if not any(t[0] == sub_id for t in tournaments):
                    tournaments.append((sub_id, False))
    
    now = datetime.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    # Aumentado para 30 dias para garantir captura de hiatos longos em playoffs ou pausas da liga
    relevant_dates = [yesterday, today] + [today + timedelta(days=i) for i in range(1, 30)]
    
    for tid, is_unique in tournaments:
        prefix = "unique-tournament" if is_unique else "tournament"
        
        # Pegar a rodada atual do torneio específico
        r_url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/rounds"
        r_data = fetch_api(session, r_url)
        if not r_data: continue
        
        current_round = r_data.get('currentRound', {}).get('round', 1)
        
        # Tenta a rodada anterior, atual e a próxima (para capturar jogos de ontem se a rodada virou)
        rounds_to_check = [current_round - 1, current_round, current_round + 1]
        
        for r_num in rounds_to_check:
            if r_num < 1: continue
            e_url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/events/round/{r_num}"
            data_events = fetch_api(session, e_url)
            if not data_events or not data_events.get('events'): 
                continue
            
            for event in data_events.get('events', []):
                ts = event.get('startTimestamp')
                if ts:
                    dt = datetime.fromtimestamp(ts).date()
                    if dt in relevant_dates:
                        status = event.get('status', {}).get('type')
                        if status != 'finished' or dt >= yesterday:
                            return True
                            
        # Fallback: Verificar last/next events se as rodadas falharam ou não encontraram nada
        for endpoint in ['last/0', 'next/0']:
            e_url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/events/{endpoint}"
            data_events = fetch_api(session, e_url)
            if data_events and data_events.get('events'):
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
                    
    # 2b. Descobrir sub-torneios de playoffs (cuptrees)
    ct_url = f"https://api.sofascore.com/api/v1/unique-tournament/{t_id}/season/{s_id}/cuptrees"
    ct_data = fetch_api(session, ct_url)
    if ct_data and 'cupTrees' in ct_data:
        for tree in ct_data['cupTrees']:
            sub_t = tree.get('tournament', {})
            sub_id = sub_t.get('id')
            sub_name = sub_t.get('name', 'Playoffs')
            if sub_id and sub_id != t_id:
                if not any(t[0] == sub_id for t in tournaments):
                    tournaments.append((sub_id, sub_name, False))
                    
    # 3. Rodadas
    for tid, label, is_unique in tournaments:
        prefix = "unique-tournament" if is_unique else "tournament"
        r_url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/rounds"
        r_data = fetch_api(session, r_url)
        rounds_fetched_count = 0
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
                events_list = e_data.get('events', []) if e_data else []
                if events_list:
                    rounds_fetched_count += len(events_list)
                    payload['rounds'].append({
                        "round_label": label,
                        "round_number": r_num,
                        "events": events_list
                    })
                    
        # Se não conseguimos buscar nenhum evento pelas rodadas normais (ex: playoffs sem endpoint de rodada ativa)
        if rounds_fetched_count == 0:
            print(f"    - {label}: Sem eventos via /events/round/. Tentando fallback paginado...")
            all_events = []
            
            # Busca jogos passados (paginado)
            for page in range(5):
                url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/events/last/{page}"
                data = fetch_api(session, url)
                if not data or not data.get('events'):
                    break
                events = data['events']
                all_events.extend(events)
                if data.get('hasNextPage') == False:
                    break
            
            # Busca jogos futuros (paginado)
            for page in range(5):
                url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/events/next/{page}"
                data = fetch_api(session, url)
                if not data or not data.get('events'):
                    break
                events = data['events']
                all_events.extend(events)
                if data.get('hasNextPage') == False:
                    break
            
            if all_events:
                # Agrupa eventos por rodada (roundInfo.round) se disponível, senão coloca na rodada original se mapeada
                rounds_map = {}
                for ev in all_events:
                    r_num = ev.get('roundInfo', {}).get('round', 1) if ev.get('roundInfo') else 1
                    if r_num not in rounds_map:
                        rounds_map[r_num] = []
                    rounds_map[r_num].append(ev)
                
                for r_num in sorted(rounds_map.keys()):
                    payload['rounds'].append({
                        "round_label": label,
                        "round_number": r_num,
                        "events": rounds_map[r_num]
                    })
                print(f"    - {label}: Fallback de sub-torneio coletou {len(all_events)} eventos em {len(rounds_map)} rodada(s).")
                    
        # Fallback agressivo: Sempre tentar pegar last/0 e next/0 para cobrir buracos
        for endpoint, r_num_fake in [('last/0', 998), ('next/0', 999)]:
            e_url = f"https://api.sofascore.com/api/v1/{prefix}/{tid}/season/{s_id}/events/{endpoint}"
            e_data = fetch_api(session, e_url)
            if e_data and e_data.get('events'):
                payload['rounds'].append({
                    "round_label": f"{label} (Fallback {endpoint})",
                    "round_number": r_num_fake,
                    "events": e_data.get('events', [])
                })
                
    return payload

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full-scan', action='store_true')
    parser.add_argument('--tor', action='store_true', help='Usar proxy Tor (127.0.0.1:9050 ou 9150)')
    parser.add_argument('--interactive', action='store_true', help='Menu interativo para escolher ligas específicas')
    args = parser.parse_args()
    
    session = requests.Session(impersonate="chrome120")
    
    if args.tor:
        # No Docker o Tor roda na 9050. No Windows local seria 9150.
        # Vamos testar a 9050 com retentativas, pois o daemon do Tor pode demorar a criar o circuito.
        proxies_9050 = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
        proxies_9150 = {"http": "socks5h://127.0.0.1:9150", "https": "socks5h://127.0.0.1:9150"}
        
        tor_ready = False
        print("🌐 Iniciando conexão com a rede Tor...")
        
        for attempt in range(1, 4):
            try:
                # Testa a porta 9050 primeiro (padrão Docker/Linux)
                session.get("https://api.ipify.org?format=json", proxies=proxies_9050, timeout=10)
                session.proxies = proxies_9050
                print("✅ Tor conectado com sucesso na porta 9050!")
                tor_ready = True
                break
            except Exception as e:
                print(f"    ⏳ Aguardando Tor ficar pronto na porta 9050... (Tentativa {attempt}/3)")
                time.sleep(3)
                
        if not tor_ready:
            try:
                # Fallback para 9150 (Tor Browser local Windows) se 9050 falhar 3 vezes
                session.get("https://api.ipify.org?format=json", proxies=proxies_9150, timeout=10)
                session.proxies = proxies_9150
                print("✅ Tor conectado com sucesso na porta 9150!")
            except Exception as e:
                print("❌ Falha crítica: Não foi possível conectar ao proxy Tor (nem 9050 nem 9150).")
                print("O IP real pode ser exposto ou a conexão falhará!")
                # Vamos forçar 9050 para evitar o erro falso de 9150 no log, já que estamos quase certeza no Docker
                session.proxies = proxies_9050

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    })
    
    # ---------------- LÓGICA DE MENU INTERATIVO ----------------
    leagues_to_process = LEAGUES
    if args.interactive:
        print("\n" + "="*50)
        print(" 📌 MENU DE SELEÇÃO DE LIGAS")
        print("="*50)
        print("[0] TODAS AS LIGAS (Padrão)")
        for i, lg in enumerate(LEAGUES, start=1):
            print(f"[{i}] {lg['country']} - {lg['name']}")
        print("="*50)
        
        try:
            escolha = input("\n👉 Digite os números das ligas que deseja atualizar separados por vírgula (ex: 1, 4, 10)\nOu pressione ENTER para todas: ").strip()
            if escolha and escolha != '0':
                indices = [int(x.strip()) for x in escolha.split(',') if x.strip().isdigit()]
                if indices:
                    leagues_to_process = [LEAGUES[i-1] for i in indices if 1 <= i <= len(LEAGUES)]
                    print(f"\n✅ Ligas selecionadas: {len(leagues_to_process)}")
                    for lg in leagues_to_process:
                        print(f"  - {lg['country']} - {lg['name']}")
                else:
                    print("\n⚠️ Seleção inválida. Atualizando TODAS as ligas.")
            else:
                print("\n✅ Atualizando TODAS as ligas.")
        except Exception as e:
            print(f"\n⚠️ Erro na seleção: {e}. Atualizando TODAS as ligas.")
            
        # Pequena pausa para o usuário ler as ligas selecionadas
        time.sleep(2)
    # -----------------------------------------------------------

    updated_leagues = []
    
    for league in leagues_to_process:
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
            if league['id'] == 384:
                filename = "payload_libertadores.json"
            elif league['id'] == 480:
                filename = "payload_sulamericana.json"
                
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
