import sys
import json
import time
import socket
from datetime import datetime
from curl_cffi import requests

def renew_tor_ip(session):
    """Solicita um novo circuito Tor (novo IP) via ControlPort 9051/9151."""
    try:
        try:
            r = session.get("https://api.ipify.org?format=json", timeout=10)
            old_ip = r.json().get("ip", "?")
        except:
            old_ip = "?"

        # Identifica a porta de controle baseada na porta de proxy
        control_port = 9051
        if hasattr(session, 'proxies') and session.proxies and "9150" in session.proxies.get("http", ""):
            control_port = 9151
            
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", control_port))
        s.send(b"AUTHENTICATE\r\n")
        resp = s.recv(256)
        if b"250" in resp:
            s.send(b"SIGNAL NEWNYM\r\n")
            resp = s.recv(256)
            if b"250" in resp:
                s.close()
                print("    ⏳ Aguardando 10s para o Tor construir novo circuito...")
                time.sleep(10)

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
    
    time.sleep(10)
    return False

def setup_tor_session():
    """Configura a sessão do requests para usar o Tor com impersonate."""
    session = requests.Session(impersonate="chrome120")
    
    # Adiciona headers padrões da Betano
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://br.betano.com",
        "Referer": "https://br.betano.com/"
    })
    
    proxies_9050 = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
    proxies_9150 = {"http": "socks5h://127.0.0.1:9150", "https": "socks5h://127.0.0.1:9150"}
    
    tor_ready = False
    print("🌐 Iniciando conexão com a rede Tor...")
    
    for attempt in range(1, 3):
        try:
            session.get("https://api.ipify.org?format=json", proxies=proxies_9050, timeout=5)
            session.proxies = proxies_9050
            print("✅ Tor conectado com sucesso na porta 9050 (Docker/Linux)!")
            tor_ready = True
            break
        except Exception:
            pass
            
    if not tor_ready:
        for attempt in range(1, 3):
            try:
                session.get("https://api.ipify.org?format=json", proxies=proxies_9150, timeout=5)
                session.proxies = proxies_9150
                print("✅ Tor conectado com sucesso na porta 9150 (Windows Local)!")
                tor_ready = True
                break
            except Exception:
                pass
                
    if not tor_ready:
        print("⚠️ Aviso: Não foi possível conectar ao proxy Tor (nem 9050 nem 9150).")
        print("🌍 Utilizando conexão direta (sem proxy)...")
        session.proxies = {}

    return session

def fetch_betano_upcoming(session):
    """
    Busca os próximos jogos de futebol na Betano.
    Retorna a lista de eventos e os mercados abertos.
    """
    # Usaremos o endpoint geral de próximos jogos com sort por ligas.
    # Pode ser trocado pelo endpoint de competições específicas se preferir.
    url = "https://br.betano.com/api/sport/futebol/jogos-de-hoje/?sort=Leagues"
    print(f"Buscando eventos da Betano em: {url}")
    
    for attempt in range(3):
        try:
            response = session.get(url, timeout=20)
            if response.status_code == 200:
                data = response.json()
                return data
                
            print(f"⚠️ Erro Betano {response.status_code}")
            if response.status_code in [403, 429, 503]:
                print("🛑 Bloqueio detectado. Solicitando novo IP...")
                if getattr(session, 'proxies', {}):
                    renew_tor_ip(session)
                else:
                    time.sleep(5) # Espera simples se não tiver Tor
                continue
                
            break
        except Exception as e:
            print(f"❌ Exceção ao acessar Betano: {e} (Tentativa {attempt+1}/3)")
            time.sleep(5)
            
    return None

def extract_odds_from_betano_data(data):
    """
    Parseia a estrutura do JSON da Altenar/Betano.
    Retorna uma lista padronizada de eventos.
    """
    events_extracted = []
    
    if not data or 'data' not in data:
        return events_extracted
        
    blocks = data['data'].get('blocks', [])
    for block in blocks:
        for ev in block.get('events', []):
            event_info = {
                'id': ev.get('id'),
                'home_team': '',
                'away_team': '',
                'start_time': ev.get('startTime'),
                'markets': {}
            }
            
            # O nome do evento vem como "Time A - Time B"
            name = ev.get('name', '')
            if ' - ' in name:
                parts = name.split(' - ')
                event_info['home_team'] = parts[0].strip()
                event_info['away_team'] = parts[1].strip()
                
            # Parse markets
            for m in ev.get('markets', []):
                # O mercado "Resultado Final" geralmente tem seleções 1, X, 2
                if m.get('name') == 'Resultado Final':
                    selections = m.get('selections', [])
                    for s in selections:
                        sel_name = s.get('name', '')
                        price = s.get('price', 0.0)
                        if sel_name == '1':
                            event_info['markets']['home_win'] = price
                        elif sel_name == 'X':
                            event_info['markets']['draw'] = price
                        elif sel_name == '2':
                            event_info['markets']['away_win'] = price
                            
                elif m.get('name') == 'Ambas equipes Marcam':
                    selections = m.get('selections', [])
                    for s in selections:
                        if s.get('name') == 'Sim':
                            event_info['markets']['btts_yes'] = s.get('price', 0.0)
                        elif s.get('name') == 'Não':
                            event_info['markets']['btts_no'] = s.get('price', 0.0)
                            
                elif 'Mais/Menos' in m.get('name') and '2.5' in m.get('name'):
                    selections = m.get('selections', [])
                    for s in selections:
                        if s.get('name') == 'Mais de':
                            event_info['markets']['over_25'] = s.get('price', 0.0)
                        elif s.get('name') == 'Menos de':
                            event_info['markets']['under_25'] = s.get('price', 0.0)
                            
            if event_info['home_team'] and event_info['away_team']:
                events_extracted.append(event_info)
                
    return events_extracted
