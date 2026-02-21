
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import League, Team, Match, Season
from datetime import datetime, timedelta
import pytz
from django.utils import timezone

class Command(BaseCommand):
    help = 'Scraper do SoccerStats para o Brasileirão (Substitui Sofascore)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando Scraper SoccerStats para Brasileirão...'))
        
        # Configurações
        country = "Brasil"
        season_year = 2026
        
        # Tenta URL do ano corrente ou específico
        # Como estamos em 2026, league=brazil deve ser 2026 se já começou, ou 2025 se não.
        # Vamos tentar forçar 2026 se possível, mas soccerstats usa sufixo _YYYY
        urls = [
            "https://www.soccerstats.com/latest.asp?league=brazil",
            f"https://www.soccerstats.com/results.asp?league=brazil_{season_year}&pmtype=bydate",
            "https://www.soccerstats.com/results.asp?league=brazil&pmtype=bydate" # Fallback
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Garantir Liga e Temporada
        league_obj = (
            League.objects.filter(name="Brasileirão", country=country).first()
            or League.objects.filter(name="Brasileirao", country=country).first()
        )
        if not league_obj:
            league_obj = League.objects.create(name="Brasileirão", country=country)
        self.stdout.write(f"League ID: {league_obj.id}, Name: {league_obj.name}")
        season_obj, _ = Season.objects.get_or_create(year=season_year)

        content = None
        used_url = ""

        for url in urls:
            self.stdout.write(f"Tentando URL: {url}")
            try:
                response = requests.get(url, headers=headers, timeout=20)
                if response.status_code == 200:
                    content = response.content
                    used_url = url
                    self.stdout.write(self.style.SUCCESS(f"Dados obtidos de {url}"))
                    break
                else:
                    self.stdout.write(self.style.WARNING(f"Falha ao acessar {url}: {response.status_code}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao acessar {url}: {e}"))

        if not content:
            self.stdout.write(self.style.ERROR("Não foi possível obter dados do SoccerStats para 2026."))
            return

        soup = BeautifulSoup(content, 'html.parser')
        
        # Encontrar tabelas de jogos
        # Estrutura específica do latest.asp (Matches section)
        # Linhas têm: 
        # td[0]: Data (ex: "Tue 24 Feb")
        # td[1]: Times separados por <br> (ex: "Flamengo<br>Mirassol")
        # td[2]: Placar ou status (ex: "pp." ou "2:1")
        
        match_count = 0
        rows = soup.find_all('tr')
        self.stdout.write(f"Analisando {len(rows)} linhas encontradas...")

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3: continue
            
            # Verificação da estrutura (Times no col[1] com <br>)
            teams_cell = cols[1]
            if not teams_cell.find('br'):
                # self.stdout.write(f"DEBUG: Sem BR na col 1: {teams_cell}")
                continue
                
            # Extrair times
            teams_text = teams_cell.get_text(separator="|", strip=True)
            # self.stdout.write(f"DEBUG: Teams Text: {teams_text}")

            if "|" not in teams_text:
                continue
                
            parts = teams_text.split("|")
            if len(parts) < 2:
                continue
                
            home_name_raw = parts[0].strip()
            away_name_raw = parts[-1].strip() # Pega o último caso tenha lixo no meio

            # Ignorar linhas lixo que viram time "MATCHES" ou similar
            home_lower = home_name_raw.lower()
            away_lower = away_name_raw.lower()
            if home_lower in ["matches", "match"] or away_lower in ["matches", "match"]:
                continue
            
            # Extrair Data
            date_cell = cols[0]
            date_text = date_cell.get_text(" ", strip=True) # "Tue 24 Feb"
            
            # Ignorar cabeçalhos ou linhas inválidas
            if not date_text or len(date_text) < 5:
                continue

            # self.stdout.write(f"DEBUG: Candidato: {date_text} | {home_name_raw} vs {away_name_raw}")


            # Parse da Data
            try:
                # Ex: "Tue 24 Feb" ou "Wed 25 Feb 00:00" -> precisamos adicionar ano 2026
                # Vamos focar em encontrar "DD MMM"
                import re
                
                # Mapa de meses
                months = {
                    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                }
                
                # Procura por "25 Feb" ou "25Feb"
                date_match = re.search(r'(\d{1,2})\s*([A-Za-z]{3})', date_text)
                
                if not date_match:
                    continue
                    
                day = int(date_match.group(1))
                month_str = date_match.group(2)
                
                # Tenta converter o mês
                month = months.get(month_str)
                if not month:
                    continue
                
                # Horário
                # Verificando se tem texto de hora na célula 0
                cell_text_full = date_cell.get_text(" ", strip=True)
                
                hour = 16 # Default
                minute = 0
                
                time_match = re.search(r'(\d{1,2}):(\d{2})', cell_text_full)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                
                match_date = datetime(season_year, month, day, hour, minute)
                # Vamos salvar como aware UTC
                match_date = timezone.make_aware(match_date, pytz.UTC)
                
            except Exception as e:
                self.stdout.write(f"Erro ao parsear data '{date_text}': {e}")
                continue

            # Resolver Times
            home_team = self.resolve_team(home_name_raw, league_obj)
            away_team = self.resolve_team(away_name_raw, league_obj)
            
            if not home_team or not away_team:
                # self.stdout.write(f"DEBUG: Time não encontrado: {repr(home_name_raw)} ou {repr(away_name_raw)}")
                continue

            # Extrair Scores
            home_score = None
            away_score = None
            status = "Scheduled"
            
            if len(cols) > 2:
                # Verificar status na col 2
                status_text = cols[2].get_text(strip=True).lower()
                
                if "pp" in status_text or "postp" in status_text:
                    status = "Postponed"
                elif "-" in status_text:
                    # Tenta extrair placar "2 - 1"
                    try:
                        score_parts = status_text.split("-")
                        if len(score_parts) == 2:
                            h = score_parts[0].strip()
                            a = score_parts[1].strip()
                            if h.isdigit() and a.isdigit():
                                home_score = int(h)
                                away_score = int(a)
                                status = "Finished"
                    except:
                        pass

            # Salvar no Banco
            try:
                if timezone.is_naive(match_date):
                    match_date = timezone.make_aware(match_date, pytz.UTC)
            except Exception as e:
                self.stdout.write(f"DEBUG: Date Error: {e}")
                continue

            # self.stdout.write(f"DEBUG: Saving {home_team} (ID:{home_team.id}) vs {away_team} (ID:{away_team.id}) at {match_date}")
            
            try:
                match, created = Match.objects.update_or_create(
                    league=league_obj,
                    season=season_obj,
                    home_team=home_team,
                    away_team=away_team,
                    defaults={
                        "date": match_date,
                        "status": status,
                        "home_score": home_score,
                        "away_score": away_score,
                        "round_name": "Regular Season" # SoccerStats latest não mostra rodada fácil
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Criado: {match}"))
                else:
                    self.stdout.write(f"Atualizado: {match}")
                
                match_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao salvar match: {e}"))
                continue

        self.stdout.write(self.style.SUCCESS(f"Processamento concluído. {match_count} jogos processados."))

        # Rodar limpeza de times ruins/lixo (CA Mineiro, MATCHES, etc.)
        try:
            self.stdout.write(self.style.SUCCESS("Executando cleanup_brazil_bad_teams para consolidar times..."))
            call_command("cleanup_brazil_bad_teams")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao executar cleanup_brazil_bad_teams: {e}"))


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
            "Chapecoense AF": "Chapecoense",
            "CA Mineiro": "Atletico-MG",
            "CA Paranaense": "Athletico-PR",
            "Coritiba FBC": "Coritiba",
            "Clube do Remo": "Remo",
            "Red Bull Bragantino": "Bragantino",
            "Brusque FC": "Brusque",
            "Amazonas FC": "Amazonas",
            "Operário Ferroviário": "Operario",
            "Botafogo FC SP": "Botafogo-SP",
            "Botafogo SP": "Botafogo-SP",
            "Guarani FC": "Guarani",
            "Ponte Preta": "Ponte Preta",
            "Ituano FC": "Ituano",
            "CRB": "CRB",
        }

        target_name = mapping.get(name, name)
        
        # Busca exata pelo nome mapeado
        team = Team.objects.filter(name__iexact=target_name, league=league).first()
        if team: return team
        
        # Busca por parte do nome
        team = Team.objects.filter(name__icontains=target_name, league=league).first()
        if team: return team

        self.stdout.write(self.style.WARNING(f"Time não encontrado no banco: '{name}' (Mapeado para: '{target_name}')"))
        return None
