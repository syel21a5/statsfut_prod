import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random

def scrape_besoccer_live():
    url = "https://www.besoccer.com/livescore"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/"
    }

    print(f"Buscando placares ao vivo em: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            print(f"Erro ao acessar BeSoccer: Status {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        payload = []

        # No BeSoccer, as ligas são agrupadas em divs com a classe 'comp-head' ou similares
        # Os jogos ficam dentro de blocos após esses cabeçalhos
        
        # Encontrando todos os blocos de competição
        competition_blocks = soup.select('.panel.panel-matches')
        
        for block in competition_blocks:
            # Título da liga e país
            comp_head = block.select_one('.comp-head')
            if not comp_head:
                continue
            
            league_name = comp_head.select_one('.comp-title').get_text(strip=True) if comp_head.select_one('.comp-title') else "Desconhecida"
            
            # Tenta extrair o país (geralmente tem uma flag ou texto)
            # No BeSoccer mobile/web o país as vezes está em um span ou no title
            country = "Global" # Fallback
            flag = comp_head.select_one('img.flag')
            if flag and flag.get('alt'):
                country = flag.get('alt')

            # Jogos dentro deste bloco
            matches = block.select('a.match-link')
            for match in matches:
                try:
                    # Verifica se é um jogo "Live"
                    # Jogos ao vivo geralmente têm a classe 'live' ou um indicador de minuto
                    min_tag = match.select_one('.match-min')
                    if not min_tag:
                        continue # Pula se não for ao vivo (ou se for finalizado/agendado)

                    elapsed = min_tag.get_text(strip=True).replace("'", "")
                    
                    home_team = match.select_one('.team-home .team-name').get_text(strip=True)
                    away_team = match.select_one('.team-away .team-name').get_text(strip=True)
                    
                    # Score
                    score_container = match.select_one('.marker')
                    if score_container:
                        scores = score_container.find_all('span')
                        if len(scores) >= 2:
                            home_score = scores[0].get_text(strip=True)
                            away_score = scores[1].get_text(strip=True)
                        else:
                            # Tenta fallback se os spans não estiverem lá
                            score_text = score_container.get_text(strip=True)
                            if '-' in score_text:
                                home_score, away_score = score_text.split('-')
                            else:
                                continue
                    else:
                        continue

                    payload.append({
                        'league': league_name,
                        'country': country,
                        'home_team': home_name,
                        'away_team': away_name,
                        'home_score': home_score,
                        'away_score': away_score,
                        'status': 'Live',
                        'elapsed': elapsed
                    })
                except Exception as e:
                    print(f"Erro ao processar jogo: {e}")

        return payload

    except Exception as e:
        print(f"Erro no scraper: {e}")
        return []

if __name__ == "__main__":
    results = scrape_besoccer_live()
    print(f"Encontrados {len(results)} jogos ao vivo.")
    
    # Salva o payload.json
    with open('payload_besoccer.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print("Arquivo payload_besoccer.json gerado com sucesso.")
