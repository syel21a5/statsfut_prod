import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season, LeagueStanding
from datetime import datetime
import time

class Command(BaseCommand):
    help = 'Scraper de dados de futebol para alimentar o BetStats'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando Scraper de Histórico (7 anos)...'))
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Criar a liga (se não existir)
        # Nota: Estamos assumindo Premier League como padrão para este script por enquanto.
        league_obj, _ = League.objects.get_or_create(name="Premier League", country="Inglaterra")
        
        current_year = datetime.now().year
        years_to_scrape = range(current_year, current_year - 7, -1)

        for year in years_to_scrape:
            if year == current_year:
                continue
            url = f"https://www.soccerstats.com/latest.asp?league=england_{year}"
            season_str = f"{year-1}/{year}"

            self.stdout.write(f"Iniciando temporada {season_str} (Ano: {year}) - URL: {url}")
            
            # Garantir Season no banco
            season_obj, _ = Season.objects.get_or_create(year=year)

            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Encontrar a tabela de classificação. 
                    # Geralmente é uma table com class 'standing-table' ou similar, ou procuramos por estrutura.
                    # No soccerstats, a tabela principal geralmente está dentro de um div id='content' > ...
                    # Vamos tentar encontrar pela estrutura de cabeçalho comuns: 'GP', 'W', 'D', 'L', 'Pts'
                    
                    # Estrategia: Encontrar todas as tabelas e ver qual tem os cabeçalhos esperados
                    tables = soup.find_all('table')
                    standing_table = None
                    
                    for table in tables:
                        # Verifica se tem cabeçalho de classificação
                        if "Pts" in table.text and "GD" in table.text and "GP" in table.text:
                            # Filtro extra para evitar tabelas pequenas de "Wide margins" etc
                            rows = table.find_all('tr')
                            if len(rows) > 15: # Premier league tem 20 times + header
                                standing_table = table
                                break
                    
                    if standing_table:
                        self.stdout.write(self.style.SUCCESS(f"Tabela encontrada para {season_str}. Processando linhas..."))
                        rows = standing_table.find_all('tr')
                        
                        count_saved = 0
                        for row in rows:
                            cols = row.find_all('td')
                            # Precisamos de linhas com dados, ignorando headers.
                            # Geralmente row com dados tem muitas colunas numéricas.
                            
                            # Estrutura típica SoccerStats (pode variar coluna, ajustaremos com teste):
                            # [Pos] [TeamName] [GP] [W] [D] [L] [GF] [GA] [GD] [Pts] ...
                            # Mas as vezes as colunas mudam. Vamos tentar parsing posicional seguro.
                            
                            if len(cols) < 8:
                                continue
                                
                            try:
                                # Tentativa de extrair nome do time
                                # O nome geralmente é o segundo td, ou está dentro de um link/font
                                team_cell = cols[1]
                                team_name = team_cell.get_text(strip=True)
                                
                                # Verifica se é um cabeçalho repetido
                                if team_name in ["Team", "Squad"]: 
                                    continue
                                    
                                # Se o Team Name for vazio ou nulo, pular
                                if not team_name:
                                    continue

                                # Pegar dados numéricos. Assume ordem padrão (pode precisar ajuste se site mudar)
                                # Geralmente: Pos (0), Team (1), GP (2), W (3), D (4), L (5), GF (6), GA (7), GD (8), Pts (9)
                                # Vamos verificar se as colunas são numéricas para confirmar
                                
                                try:
                                    gp = int(cols[2].get_text(strip=True))
                                    w = int(cols[3].get_text(strip=True))
                                    d = int(cols[4].get_text(strip=True))
                                    l = int(cols[5].get_text(strip=True))
                                    gf = int(cols[6].get_text(strip=True))
                                    ga = int(cols[7].get_text(strip=True))
                                    pts = int(cols[9].get_text(strip=True))
                                    
                                    # A posição as vezes é a col 0, mas as vezes é vazia no site
                                    # Vamos tentar col 0, se falhar, calculamos baseado no loop
                                    try:
                                        pos = int(cols[0].get_text(strip=True))
                                    except:
                                        pos = count_saved + 1

                                    # Salvar Time
                                    team_obj, _ = Team.objects.get_or_create(name=team_name, league=league_obj)
                                    
                                    # Salvar Standing
                                    LeagueStanding.objects.update_or_create(
                                        league=league_obj,
                                        season=season_obj,
                                        team=team_obj,
                                        defaults={
                                            'position': pos,
                                            'played': gp,
                                            'won': w,
                                            'drawn': d,
                                            'lost': l,
                                            'goals_for': gf,
                                            'goals_against': ga,
                                            'points': pts
                                        }
                                    )
                                    count_saved += 1
                                    
                                except ValueError:
                                    # Linha não é de dados (pode ser separador)
                                    continue

                            except Exception as e_row:
                                # Erro pontual na linha
                                pass
                        
                        self.stdout.write(f"Salvos {count_saved} times para {season_str}.")
                        
                    else:
                         self.stdout.write(self.style.WARNING(f"Não foi possível identificar a tabela de classificação em {url}"))

                else:
                    self.stdout.write(self.style.ERROR(f"Erro HTTP {response.status_code} em {url}"))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar {season_str}: {e}"))
            
            # Pausa para ser gentil com o servidor
            time.sleep(3)

        self.stdout.write(self.style.SUCCESS('Carga de histórico finalizada!'))

