import time
import requests as basic_requests
from curl_cffi import requests
from datetime import datetime, timezone
import traceback
from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season
from django.db import transaction

# Default Constants for Australian A-League Men
TOURNAMENT_ID = 136
DEFAULT_SEASON_ID = 82603
DEFAULT_YEAR = 2026

class Command(BaseCommand):
    help = "Faz o scraping das partidas da Austrália A-League Men (SofaScore) de forma invisível via curl_cffi"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session(impersonate="chrome110")
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Origin": "https://www.sofascore.com",
            "Referer": "https://www.sofascore.com/"
        })

    def fetch_api(self, url):
        try:
            time.sleep(1.5)  # Respect rate limits
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                self.stdout.write(self.style.ERROR(f"Erro na API {url}: Status {response.status_code}"))
                return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Exceção ao acessar {url}: {e}"))
            return None

    def add_arguments(self, parser):
        parser.add_argument(
            '--season_id',
            type=int,
            help='ID da temporada no SofaScore'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Ano de término da temporada para o banco de dados'
        )

    def handle(self, *args, **kwargs):
        in_season_id = kwargs.get('season_id')
        in_year = kwargs.get('year')
        
        season_id = in_season_id if in_season_id else DEFAULT_SEASON_ID
        season_year = in_year if in_year else DEFAULT_YEAR

        self.stdout.write(self.style.SUCCESS(f"Iniciando importação do SofaScore (Austrália) para a Temporada {season_year} (Sofa_ID: {season_id})..."))

        # 1. Pegar/Criar a Liga e a Temporada com IDs FIXOS da Produção
        league, _ = League.objects.get_or_create(
            id=21,  # ID da Liga na Produção
            defaults={
                "name": "A-League Men",
                "country": "Australia",
                "division": 1,
                "soccerstats_slug": "australia"
            }
        )
        season, _ = Season.objects.get_or_create(
            id=1,  # ID da Season 2026 na Produção
            defaults={
                "year": season_year
            }
        )

        # 2. Obter Teams (Standings é um bom lugar para puxar os IDs dos times da temporada)
        self.stdout.write("Buscando times da temporada...")
        standings_url = f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{season_id}/standings/total"
        standings_data = self.fetch_api(standings_url)
        
        teams_map = {} # SofaScore ID -> Team Object
        if standings_data and 'standings' in standings_data:
            standings_list = standings_data['standings'][0].get('rows', [])
            for row in standings_list:
                team_data = row.get('team', {})
                team_id = str(team_data.get('id'))
                team_name = team_data.get('name')
                
                if team_id and team_name:
                    team, created = Team.objects.get_or_create(
                        api_id=f"sofa_{team_id}",
                        defaults={
                            "name": team_name,
                            "league": league
                        }
                    )
                    if not created and team.league != league: # Just to be safe
                        team.league = league
                        team.save()
                    teams_map[int(team_id)] = team
                    
            self.stdout.write(self.style.SUCCESS(f"{len(teams_map)} times carregados/criados."))
        else:
            self.stdout.write(self.style.ERROR("Não foi possível carregar a tabela de times para a Austrália. Abortando."))
            return

        # 3. Obter todas as partidas da temporada
        rounds_url = f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{season_id}/rounds"
        rounds_data = self.fetch_api(rounds_url)
        
        if not rounds_data or 'rounds' not in rounds_data:
            self.stdout.write(self.style.ERROR("Falha ao obter rodadas. Fim."))
            return
            
        current_round = rounds_data.get('currentRound', {}).get('round', 1)
        total_rounds = len(rounds_data['rounds'])
        
        self.stdout.write(self.style.SUCCESS(f"A liga tem {total_rounds} rodadas. (Rodada atual: {current_round})"))

        matches_created = 0
        matches_updated = 0

        # Iterar sobre todas as rodadas
        for round_info in rounds_data['rounds']:
            round_number = round_info['round']
            self.stdout.write(f"Processando Rodada {round_number}...")
            
            events_url = f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{season_id}/events/round/{round_number}"
            events_data = self.fetch_api(events_url)
            
            if not events_data or 'events' not in events_data:
                continue
                
            with transaction.atomic():
                for ev in events_data['events']:
                    fixture_id = str(ev.get('id'))
                    match_api_id = f"sofa_{fixture_id}"
                    
                    home_data = ev.get('homeTeam', {})
                    away_data = ev.get('awayTeam', {})
                    home_sofa_id = home_data.get('id')
                    away_sofa_id = away_data.get('id')
                    
                    start_timestamp = ev.get('startTimestamp')
                    match_date = datetime.fromtimestamp(start_timestamp, tz=timezone.utc) if start_timestamp else None
                    
                    status_type = ev.get('status', {}).get('type')
                    
                    # Map Status
                    match_status = "Scheduled"
                    if status_type == 'finished':
                        match_status = "FT"
                    elif status_type == 'inprogress':
                        match_status = "In Play"
                    elif status_type == 'canceled':
                        match_status = "Cancelled"
                    elif status_type == 'postponed':
                        match_status = "Postponed"
                    
                    # Scores
                    home_score = ev.get('homeScore', {}).get('current')
                    away_score = ev.get('awayScore', {}).get('current')
                    
                    # Find DB Teams
                    home_team = teams_map.get(int(home_sofa_id))
                    away_team = teams_map.get(int(away_sofa_id))
                    
                    if not home_team or not away_team:
                        self.stdout.write(self.style.WARNING(f"Time não encontrado no mapa para o evento {fixture_id}. Ignorando."))
                        continue
                    
                    # Create or Update Match
                    match, created = Match.objects.update_or_create(
                        api_id=match_api_id,
                        defaults={
                            "league": league,
                            "season": season,
                            "home_team": home_team,
                            "away_team": away_team,
                            "date": match_date,
                            "round_name": f"Round {round_number}",
                            "status": match_status,
                            "home_score": home_score,
                            "away_score": away_score,
                        }
                    )
                    
                    if created:
                        matches_created += 1
                    else:
                        matches_updated += 1
                        
        self.stdout.write(self.style.SUCCESS(f"Concluído! {matches_created} partidas criadas, {matches_updated} atualizadas."))

