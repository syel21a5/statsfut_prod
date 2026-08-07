import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import League, Team, Match, Season
from matches.utils import normalize_team_name
import datetime
import re

class Command(BaseCommand):
    help = 'Scrape Australia A-League results from SoccerStats'

    def handle(self, *args, **options):
        with open('scrape_log.txt', 'w', encoding='utf-8') as f:
            f.write('Iniciando scraper da Austrália (SoccerStats)...\n')
        
        # 1. Configurar League e Season
        try:
            league = League.objects.get(name="A League", country="Australia")
        except League.DoesNotExist:
            with open('scrape_log.txt', 'a', encoding='utf-8') as f:
                f.write('Liga "A League" (Australia) não encontrada!\n')
            return

        # Estamos em Fev 2026, então a temporada é 2025/2026 -> Season 2026
        season, _ = Season.objects.get_or_create(year=2026)
        
        url = "https://www.soccerstats.com/results.asp?league=australia&pmtype=bydate"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
        except Exception as e:
            with open('scrape_log.txt', 'a', encoding='utf-8') as f:
                f.write(f'Erro ao baixar URL: {e}\n')
            return

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # SoccerStats results table is often straightforward
        # Look for rows with dates and scores
        
        # A estrutura varia, mas geralmente é uma tabela com class 'odd' e 'even' rows ou similar
        # Vamos procurar todas as tabelas e tentar identificar a correta
        
        tables = soup.find_all('table')
        self.stdout.write(f'Encontradas {len(tables)} tabelas. Analisando...')
        
        count_created = 0
        count_updated = 0
        
        # Regex para identificar linhas de jogo
        # Data format: "25 Feb" or similar.
        # Mas SoccerStats results page usually has a specific table structure
        
        rows = soup.find_all('tr', class_='odd') + soup.find_all('tr', class_='trow3')
        
        with open('scrape_log.txt', 'a', encoding='utf-8') as f:
            f.write(f'Encontradas {len(rows)} linhas na tabela.\n')
        
        created_count = 0
        updated_count = 0

        raw_teams = set()

        for row in rows:
            cols = row.find_all('td')
            if not cols: continue
            
            # Date
            date_text = cols[0].get_text(strip=True)
            
            # Debug log for first few rows
            if created_count + updated_count < 5:
                with open('scrape_log.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Processing row: {date_text} | Cols len: {len(cols)}\n")

            # Try parse date
            try:
                # Format could be "25 Feb" or "Fri 25 Feb"
                parts = date_text.split()
                if len(parts) == 2:
                    day, month_str = parts
                elif len(parts) == 3:
                    _, day, month_str = parts # Ignore weekday
                else:
                    # with open('scrape_log.txt', 'a', encoding='utf-8') as f:
                    #     f.write(f"Date format unknown: {date_text}\n")
                    continue
                
                # Assuming 2025/2026 season. If month is Aug-Dec -> 2025, Jan-May -> 2026
                # But safer to just guess based on current date?
                # SoccerStats usually current season.
                # Let's map months
                months = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                month = months.get(month_str)
                if not month: continue
                
                year = 2026 if month < 7 else 2025
                match_date = datetime.datetime(year, month, int(day))
                # match_date = timezone.make_aware(match_date) # Wait, make_aware needs settings configured or manual timezone
                # Use pytz or timezone.utc if settings not reliable here, but timezone.make_aware uses DEFAULT_TIME_ZONE
                match_date = timezone.make_aware(match_date)
            except Exception as e:
                with open('scrape_log.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Date error: {date_text} -> {e}\n")
                continue

            # As colunas variam. Vamos tentar identificar pelo score
            score_col_idx = -1
            for idx, col in enumerate(cols):
                txt = col.get_text(strip=True)
                # Verifica formato "2:1" ou "2-1"
                if re.match(r'^\d+\s*[:\-]\s*\d+$', txt):
                    score_col_idx = idx
                    break
            
            if score_col_idx == -1:
                continue

            # Check if date is in the future
            is_future = match_date > timezone.now()
            
            try:
                home_team_name = cols[score_col_idx-1].get_text(strip=True)
                away_team_name = cols[score_col_idx+1].get_text(strip=True)
                score_text = cols[score_col_idx].get_text(strip=True)
                
                # Parse Score (pode ser : ou -)
                sep = ':' if ':' in score_text else '-'
                
                h_score = None
                a_score = None
                status = 'Scheduled'

                if not is_future:
                    try:
                        h_score, a_score = map(int, score_text.split(sep))
                        status = 'Finished'
                        
                        if h_score > 15 or a_score > 15:
                             h_score = None
                             a_score = None
                             status = 'Scheduled'
                    except ValueError:
                         pass

                # Normalize names (basic)
                home_team_name = home_team_name.strip()
                away_team_name = away_team_name.strip()
                
                raw_teams.add(home_team_name)
                raw_teams.add(away_team_name)
                
                # Resolve Teams
                norm_home = normalize_team_name(home_team_name)
                home_team = Team.objects.filter(name__iexact=norm_home, league=league).first()
                if not home_team:
                    home_team, _ = Team.objects.get_or_create(name=norm_home, league=league)

                norm_away = normalize_team_name(away_team_name)
                away_team = Team.objects.filter(name__iexact=norm_away, league=league).first()
                if not away_team:
                    away_team, _ = Team.objects.get_or_create(name=norm_away, league=league)
                
                # Create/Update Match
                match, created = Match.objects.update_or_create(
                    league=league,
                    season=season,
                    home_team=home_team,
                    away_team=away_team,
                    date=match_date,
                    defaults={
                        'home_score': h_score,
                        'away_score': a_score,
                        'status': status
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                    
            except Exception as e:
                with open('scrape_log.txt', 'a', encoding='utf-8') as f:
                    f.write(f"Error parsing row {date_text}: {e}\n")
                continue

        self.stdout.write(self.style.SUCCESS(f"Scraper finalizado! Criados: {created_count}, Atualizados: {updated_count}"))
        self.stdout.write(self.style.SUCCESS(f"Times encontrados: {sorted(list(raw_teams))}"))

        # Automatically recalculate standings
        if created_count > 0 or updated_count > 0:
            self.stdout.write(self.style.SUCCESS("Recalculando tabela de classificação..."))
            from django.core.management import call_command
            call_command('recalculate_standings', league_name='A League', country='Australia')
        else:
            self.stdout.write(self.style.WARNING("Nenhuma alteração nos jogos, pulando recálculo de tabela."))
