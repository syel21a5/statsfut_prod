import sys
import json
import time
import socket
from datetime import datetime
from curl_cffi import requests

def setup_proxy_session():
    """Configura a sessão do requests para usar o proxy residencial DataImpulse com impersonate."""
    session = requests.Session(impersonate="chrome120")
    
    # Adiciona headers padrões da Betano
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://br.betano.com",
        "Referer": "https://br.betano.com/",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    })
    
    # Suas credenciais DataImpulse (Pool Residencial Brasil)
    # Adicionamos __cr.br ao login para forçar que a rotação traga APENAS IPs do Brasil
    proxy_url = "http://fd01c63d380fd264da00__cr.br:a221e91446283ce8@gw.dataimpulse.com:823"
    proxies = {"http": proxy_url, "https": proxy_url}
    
    print("🌐 Iniciando conexão com Proxy Residencial (DataImpulse/Brasil)...")
    session.proxies = proxies
    
    try:
        r = session.get("https://api.ipify.org?format=json", timeout=15)
        ip = r.json().get("ip", "?")
        print(f"✅ Conectado com sucesso via Proxy! IP de saída: {ip}")
    except Exception as e:
        print(f"⚠️ Aviso: Falha ao testar proxy (api.ipify.org): {e}")

    return session

def fetch_betano_upcoming(session):
    """
    Busca os próximos jogos de futebol na Betano.
    Retorna a lista de eventos e os mercados abertos.
    """
    # O endpoint proximas-24-horas garante que peguemos os jogos de hoje e também os de amanhã
    url = "https://br.betano.com/api/sport/futebol/proximas-24-horas/?sort=Leagues"
    print(f"Buscando eventos da Betano em: {url}")
    
    for attempt in range(3):
        try:
            response = session.get(url, timeout=25)
            if response.status_code == 200:
                data = response.json()
                return data
                
            print(f"⚠️ Erro Betano {response.status_code}")
            if response.status_code in [403, 429, 503]:
                print("🛑 Bloqueio detectado. O proxy rotativo vai trocar de IP a cada request, aguardando 5s...")
                time.sleep(5)
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
                m_name = m.get('name', '')
                selections = m.get('selections', [])
                
                if m_name == 'Resultado Final':
                    for s in selections:
                        sel_name = s.get('name', '')
                        if sel_name == '1': event_info['markets']['home_win'] = s.get('price', 0.0)
                        elif sel_name == 'X': event_info['markets']['draw'] = s.get('price', 0.0)
                        elif sel_name == '2': event_info['markets']['away_win'] = s.get('price', 0.0)
                        
                elif m_name == 'Ambas equipes Marcam':
                    for s in selections:
                        if s.get('name') == 'Sim': event_info['markets']['btts_yes'] = s.get('price', 0.0)
                        elif s.get('name') == 'Não': event_info['markets']['btts_no'] = s.get('price', 0.0)
                        
                elif 'Empate Anula' in m_name:
                    if len(selections) >= 2:
                        event_info['markets']['dnb_home'] = selections[0].get('price', 0.0)
                        event_info['markets']['dnb_away'] = selections[1].get('price', 0.0)

                elif 'Dupla chance' in m_name and 'Mais/Menos' not in m_name and 'Ambas' not in m_name:
                    for s in selections:
                        if s.get('name') in ['1X', 'Casa/Empate']: event_info['markets']['dc_1x'] = s.get('price', 0.0)
                        elif s.get('name') in ['X2', 'Empate/Fora']: event_info['markets']['dc_x2'] = s.get('price', 0.0)

                elif 'Dupla chance e Ambas' in m_name:
                    for s in selections:
                        sn = s.get('name', '')
                        if '1X' in sn and 'Sim' in sn: event_info['markets']['dc_1x_btts_yes'] = s.get('price', 0.0)
                        elif '1X' in sn and 'Não' in sn: event_info['markets']['dc_1x_btts_no'] = s.get('price', 0.0)
                        elif 'X2' in sn and 'Sim' in sn: event_info['markets']['dc_x2_btts_yes'] = s.get('price', 0.0)
                        elif 'X2' in sn and 'Não' in sn: event_info['markets']['dc_x2_btts_no'] = s.get('price', 0.0)

                elif 'Dupla chance e' in m_name and 'Mais/Menos' in m_name:
                    for s in selections:
                        sn = s.get('name', '')
                        if '1X' in sn and 'Mais de 1.5' in sn: event_info['markets']['dc_1x_over_15'] = s.get('price', 0.0)
                        elif '1X' in sn and 'Mais de 2.5' in sn: event_info['markets']['dc_1x_over_25'] = s.get('price', 0.0)
                        elif '1X' in sn and 'Mais de 3.5' in sn: event_info['markets']['dc_1x_over_35'] = s.get('price', 0.0)
                        elif 'X2' in sn and 'Mais de 1.5' in sn: event_info['markets']['dc_x2_over_15'] = s.get('price', 0.0)
                        elif 'X2' in sn and 'Mais de 2.5' in sn: event_info['markets']['dc_x2_over_25'] = s.get('price', 0.0)
                        elif 'X2' in sn and 'Mais de 3.5' in sn: event_info['markets']['dc_x2_over_35'] = s.get('price', 0.0)

                elif '1º Tempo' in m_name and 'Mais/Menos' in m_name and '0.5' in m_name:
                    for s in selections:
                        if 'Mais de' in s.get('name', ''): event_info['markets']['ht_goal'] = s.get('price', 0.0)

                elif 'Escanteios' in m_name:
                    if 'Mais/Menos' in m_name:
                        line = ''
                        if '6.5' in m_name: line = '65'
                        elif '7.5' in m_name: line = '75'
                        elif '8.5' in m_name: line = '85'
                        elif '9.5' in m_name: line = '95'
                        elif '10.5' in m_name: line = '105'
                        elif '11.5' in m_name: line = '115'
                        if line:
                            for s in selections:
                                if 'Mais de' in s.get('name', ''): event_info['markets'][f'corners_over_{line}'] = s.get('price', 0.0)
                    elif '1X2' in m_name or 'Vencedor' in m_name or 'Resultado Final' in m_name:
                        for s in selections:
                            if s.get('name') == '1': event_info['markets']['corners_home_win'] = s.get('price', 0.0)
                            elif s.get('name') == 'X': event_info['markets']['corners_draw'] = s.get('price', 0.0)
                            elif s.get('name') == '2': event_info['markets']['corners_away_win'] = s.get('price', 0.0)

                elif 'Sem Sofrer Gols' in m_name or 'Manter sua rede intacta' in m_name:
                    if event_info['home_team'] in m_name:
                        for s in selections:
                            if s.get('name') == 'Sim': event_info['markets']['clean_sheet_home'] = s.get('price', 0.0)
                    elif event_info['away_team'] in m_name:
                        for s in selections:
                            if s.get('name') == 'Sim': event_info['markets']['clean_sheet_away'] = s.get('price', 0.0)

                elif 'Mais/Menos' in m_name and '1º Tempo' not in m_name and 'Escanteios' not in m_name and 'Cartões' not in m_name:
                    line = ''
                    if '1.5' in m_name: line = '15'
                    elif '2.5' in m_name: line = '25'
                    elif '3.5' in m_name: line = '35'
                    elif '4.5' in m_name: line = '45'
                    elif '5.5' in m_name: line = '55'
                    
                    if line:
                        for s in selections:
                            if 'Mais de' in s.get('name', ''):
                                event_info['markets'][f'over_{line}'] = s.get('price', 0.0)
                            elif 'Menos de' in s.get('name', ''):
                                event_info['markets'][f'under_{line}'] = s.get('price', 0.0)
                                
            if event_info['home_team'] and event_info['away_team']:
                events_extracted.append(event_info)
                
    return events_extracted
