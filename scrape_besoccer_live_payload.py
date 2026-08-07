import json
import os
import time
from curl_cffi import requests as requests_cffi
from bs4 import BeautifulSoup

def scrape_besoccer_live():
    url = "https://www.besoccer.com/livescore"
    session = requests_cffi.Session(impersonate="chrome120")
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/"
    })

    print(f"Buscando placares ao vivo em: {url}")
    try:
        response = session.get(url, timeout=20)
        if response.status_code != 200:
            print(f"Erro ao acessar BeSoccer: Status {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        payload = []

        match_links = soup.select('a.match-link')
        
        for match in match_links:
            try:
                if match.find_parent(class_='autocomplete-box'):
                    continue

                status_tag = match.select_one('.tag-nobg.live') or match.select_one('.tag-nobg.end')
                if not status_tag:
                    continue 

                is_live = 'live' in status_tag.get('class', [])
                status_text = status_tag.get_text(strip=True)
                elapsed = status_text.replace("'", "") if is_live else status_text
                
                home_team = match.select_one('.team_left').get_text(strip=True) if match.select_one('.team_left') else None
                away_team = match.select_one('.team_right').get_text(strip=True) if match.select_one('.team_right') else None
                
                if not home_team or not away_team:
                    continue

                home_score = match.select_one('.r1').get_text(strip=True) if match.select_one('.r1') else "0"
                away_score = match.select_one('.r2').get_text(strip=True) if match.select_one('.r2') else "0"
                
                # Tenta achar o título da liga subindo na árvore ou procurando o anterior
                league_name = "Desconhecida"
                country = "Global"
                
                # Busca o cabeçalho de competição mais próximo ACIMA do jogo
                # No BeSoccer desktop, as competições ficam em divs com classes como 'comp-head' ou no topo do painel
                # Vamos tentar encontrar o título subindo até o painel e pegando o primeiro título lá
                parent_panel = match.find_parent(class_='panel')
                if parent_panel:
                    # Tenta vários seletores comuns de título
                    title_tag = parent_panel.select_one('.comp-title') or \
                                parent_panel.select_one('.head-title') or \
                                parent_panel.select_one('.panel-title') or \
                                parent_panel.select_one('.title')
                    
                    if title_tag:
                        league_name = title_tag.get_text(strip=True)
                        flag = title_tag.find_previous('img', class_='flag') or parent_panel.select_one('img.flag')
                        if flag and flag.get('alt'):
                            country = flag.get('alt')

                payload.append({
                    'league': league_name,
                    'country': country,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'status': 'Live' if is_live else 'Finished',
                    'elapsed': elapsed
                })
            except Exception:
                continue

        return payload

    except Exception as e:
        print(f"Erro no scraper: {e}")
        return []

if __name__ == "__main__":
    results = scrape_besoccer_live()
    print(f"Encontrados {len(results)} jogos (Live/FT).")
    with open('payload_besoccer.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print("Arquivo payload_besoccer.json gerado.")
