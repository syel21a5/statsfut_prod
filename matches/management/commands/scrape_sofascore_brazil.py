
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season
from datetime import datetime, timedelta
import pytz
from django.utils import timezone

class Command(BaseCommand):
    help = 'Scraper do SoccerStats para o Brasileirão (Substitui Sofascore)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando Scraper SoccerStats para Brasileirão...'))
        
        # Configurações
        league_name = "Brasileirão"
        country = "Brasil"
        season_year = 2026
        
        # Tenta URL do ano corrente ou específico
        # Como estamos em 2026, league=brazil deve ser 2026 se já começou, ou 2025 se não.
        # Vamos tentar forçar 2026 se possível, mas soccerstats usa sufixo _YYYY
        urls = [
            f"https://www.soccerstats.com/results.asp?league=brazil_{season_year}&pmtype=bydate",
            "https://www.soccerstats.com/results.asp?league=brazil&pmtype=bydate" # Fallback
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Garantir Liga e Temporada
        league_obj, _ = League.objects.get_or_create(name=league_name, country=country)
        season_obj, _ = Season.objects.get_or_create(year=season_year)

        content = None
        used_url = ""

        for url in urls:
            self.stdout.write(f"Tentando URL: {url}")
            try:
                response = requests.get(url, headers=headers, timeout=20)
                if response.status_code == 200:
                    # Verifica se é a temporada certa
                    if str(season_year) in response.text or "2026" in response.text:
                         content = response.content
                         used_url = url
                         break
                    else:
                        self.stdout.write(self.style.WARNING(f"URL {url} parece não ter dados de {season_year}."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao acessar {url}: {e}"))

        if not content:
            self.stdout.write(self.style.ERROR("Não foi possível obter dados do SoccerStats para 2026."))
            return

        soup = BeautifulSoup(content, 'html.parser')
        
        # Encontrar tabelas de jogos
        # SoccerStats estrutura: Várias tabelas, precisamos achar a que tem datas e times
        tables = soup.find_all('table')
        match_count = 0
        
        self.stdout.write(f"Analisando {len(tables)} tabelas...")

        for table in tables:
            rows = table.find_all('tr')
            if not rows: continue
            
            # Heurística: tabelas de jogos geralmente têm linhas com datas ou times e scores
            # Vamos iterar as linhas e tentar extrair
            
            current_date = None
            
            for row in rows:
                cols = row.find_all('td')
                if not cols: continue
                
                text = row.get_text(" ", strip=True)
                
                # Tenta detectar linha de data (ex: "Sat 14 Feb")
                # SoccerStats costuma colocar a data numa linha separada ou na primeira coluna
                if len(cols) == 1 or (len(cols) > 0 and "font-weight:bold" in str(cols[0])):
                    try:
                        # Tentar parsear data
                        # Formatos comuns: "Saturday 14 February 2026" ou "Round 1"
                        date_text = cols[0].get_text(strip=True)
                        # Ignorar headers de tabela
                        if "Round" in date_text or "week" in date_text.lower():
                            continue
                            
                        # Tentar converter para data
                        # Assumindo formato do site (ex: 28 Feb)
                        # Precisamos do ano.
                        pass # TODO: Implementar parse de data de cabeçalho se necessário
                    except:
                        pass

                # Linha de jogo: Home | Score/Time | Away
                # Estrutura comum: TimeA - TimeB ou TimeA 1-0 TimeB
                # Ou colunas: [Date] [Home] [Score] [Away] ...
                
                if len(cols) >= 3:
                    # Tentativa de extração baseada em posição
                    # Geralmente: Data (0), Home (1), Score (2), Away (3) ...
                    # Mas varia. Vamos procurar por células que pareçam times.
                    
                    try:
                        # Pega textos das colunas
                        col_texts = [c.get_text(strip=True) for c in cols]
                        
                        # Verifica se tem data na primeira coluna (ex: "28 Feb")
                        date_str = col_texts[0]
                        home_name = col_texts[1]
                        score_or_time = col_texts[2]
                        away_name = col_texts[3] if len(cols) > 3 else ""
                        
                        # Validação básica
                        if not home_name or not away_name: continue
                        if len(home_name) < 3 or len(away_name) < 3: continue
                        
                        # Resolver times
                        home_team = self.resolve_team(home_name, league_obj)
                        away_team = self.resolve_team(away_name, league_obj)
                        
                        if not home_team or not away_team:
                            # Tenta deslocar colunas (as vezes tem coluna extra no inicio)
                            if len(cols) > 4:
                                home_name = col_texts[2]
                                score_or_time = col_texts[3]
                                away_name = col_texts[4]
                                home_team = self.resolve_team(home_name, league_obj)
                                away_team = self.resolve_team(away_name, league_obj)
                        
                        if not home_team or not away_team:
                            continue

                        # Parse da Data e Hora
                        # date_str ex: "28 Feb"
                        # score_or_time ex: "15:00" ou "1 - 0"
                        
                        match_date = self.parse_datetime(date_str, score_or_time, season_year)
                        
                        if not match_date:
                            continue

                        # Status e Placar
                        status = "Scheduled"
                        h_score = None
                        a_score = None
                        
                        if "-" in score_or_time and ":" not in score_or_time:
                            parts = score_or_time.split("-")
                            if len(parts) == 2 and parts[0].strip().isdigit():
                                h_score = int(parts[0].strip())
                                a_score = int(parts[1].strip())
                                status = "Finished"
                        
                        # Salvar no banco
                        match, created = Match.objects.update_or_create(
                            league=league_obj,
                            season=season_obj,
                            home_team=home_team,
                            away_team=away_team,
                            defaults={
                                'date': match_date,
                                'status': status,
                                'home_score': h_score,
                                'away_score': a_score
                            }
                        )
                        
                        action = "Criado" if created else "Atualizado"
                        self.stdout.write(f"{action}: {match_date.strftime('%d/%m %H:%M')} - {home_team.name} vs {away_team.name} [{status}]")
                        match_count += 1

                    except Exception as e:
                        # self.stdout.write(f"Ignorando linha: {e}")
                        pass

        self.stdout.write(self.style.SUCCESS(f"Processamento concluído. {match_count} jogos processados."))
        
        if match_count == 0:
            self.stdout.write(self.style.WARNING("\nAVISO: Nenhum jogo foi encontrado."))
            self.stdout.write(self.style.WARNING("Possíveis causas:"))
            self.stdout.write(self.style.WARNING("1. O SoccerStats ainda não publicou a tabela do Brasileirão 2026 (comum antes de Abril)."))
            self.stdout.write(self.style.WARNING("2. A URL mudou. Tente verificar no site soccerstats.com."))
            self.stdout.write(self.style.WARNING("3. O site bloqueou o acesso (menos provável se retornou 200 OK)."))


    def parse_datetime(self, date_str, time_str, year):
        try:
            # Limpa string
            date_str = date_str.strip()
            time_str = time_str.strip()
            
            if not date_str: return None
            
            # Formatos possíveis de data: "28 Feb", "28.02", "Today"
            day = 1
            month = 1
            
            if "Today" in date_str:
                now = datetime.now()
                day = now.day
                month = now.month
            elif "Tomorrow" in date_str:
                now = datetime.now() + timedelta(days=1)
                day = now.day
                month = now.month
            else:
                # Tenta parsear "28 Feb"
                try:
                    dt = datetime.strptime(date_str, "%d %b")
                    day = dt.day
                    month = dt.month
                except:
                    return None
            
            # Hora
            hour = 0
            minute = 0
            if ":" in time_str:
                try:
                    h, m = map(int, time_str.split(":"))
                    hour = h
                    minute = m
                except:
                    pass
            
            # Cria data naive
            naive = datetime(year, month, day, hour, minute)
            
            # Adiciona Timezone (SoccerStats geralmente é UTC ou UK time. Vamos assumir UTC para simplificar e ajustar depois se necessário)
            # Se o projeto usa UTC, salvamos como UTC.
            return timezone.make_aware(naive, pytz.UTC)

        except Exception:
            return None

    def resolve_team(self, name, league):
        name = name.strip()
        
        # Mapeamento API/SoccerStats -> Nomes Canônicos do Banco
        mapping = {
            "SE Palmeiras": "Palmeiras",
            "CR Flamengo": "Flamengo",
            "Botafogo FR": "Botafogo",
            "São Paulo FC": "Sao Paulo",
            "Sao Paulo": "Sao Paulo",
            "Grêmio FBPA": "Gremio",
            "Gremio": "Gremio",
            "Clube Atlético Mineiro": "Atletico-MG",
            "Atlético Mineiro": "Atletico-MG",
            "Atletico MG": "Atletico-MG",
            "Club Athletico Paranaense": "Athletico-PR",
            "Athletico Paranaense": "Athletico-PR",
            "Athletico PR": "Athletico-PR",
            "Fluminense FC": "Fluminense",
            "Cuiabá EC": "Cuiaba",
            "Cuiaba": "Cuiaba",
            "SC Corinthians Paulista": "Corinthians",
            "Corinthians": "Corinthians",
            "Cruzeiro EC": "Cruzeiro",
            "Cruzeiro": "Cruzeiro",
            "SC Internacional": "Internacional",
            "Internacional": "Internacional",
            "Fortaleza EC": "Fortaleza",
            "Fortaleza": "Fortaleza",
            "EC Bahia": "Bahia",
            "Bahia": "Bahia",
            "CR Vasco da Gama": "Vasco",
            "Vasco da Gama": "Vasco",
            "Vasco": "Vasco",
            "EC Juventude": "Juventude",
            "Juventude": "Juventude",
            "AC Goianiense": "Atletico-GO",
            "Atlético Goianiense": "Atletico-GO",
            "Criciúma EC": "Criciuma",
            "Criciuma": "Criciuma",
            "EC Vitória": "Vitoria",
            "Vitoria": "Vitoria",
            "Red Bull Bragantino": "Bragantino",
            "RB Bragantino": "Bragantino",
            "Bragantino": "Bragantino",
            "Santos FC": "Santos",
            "Santos": "Santos",
            "Chapecoense": "Chapecoense",
            "Sport Club do Recife": "Sport Recife",
            "Sport Recife": "Sport Recife",
            "Ceará SC": "Ceara",
            "Ceara": "Ceara",
            "Goiás EC": "Goias",
            "Goias": "Goias",
            "América FC": "America-MG",
            "America MG": "America-MG",
            "Avaí FC": "Avai",
            "Avai": "Avai",
            "Coritiba FC": "Coritiba",
            "Coritiba": "Coritiba",
            "Mirassol FC": "Mirassol",
            "Mirassol": "Mirassol",
            "Clube do Remo": "Remo",
            "Remo": "Remo",
            "Paysandu SC": "Paysandu",
            "Paysandu": "Paysandu",
            "Vila Nova FC": "Vila Nova",
            "Novorizontino": "Novorizontino",
        }

        target_name = mapping.get(name, name)
        
        # Busca exata pelo nome mapeado
        team = Team.objects.filter(name__iexact=target_name, league=league).first()
        if team: return team

        # Busca exata pelo nome original
        team = Team.objects.filter(name__iexact=name, league=league).first()
        if team: return team
        
        return None
