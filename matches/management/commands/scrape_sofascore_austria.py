import time
import requests as basic_requests
from curl_cffi import requests
from datetime import datetime, timezone
import traceback
from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season
from django.db import transaction

# Default Constants for Austrian Bundesliga 2025/2026
TOURNAMENT_ID = 45
DEFAULT_SEASON_ID = 77382
DEFAULT_YEAR = 2026

TEAM_MAPPING = {
    "SK Sturm Graz": "SK Sturm Graz",
    "Salzburg": "Salzburg",
    "FK Austria Wien": "Austria Wien",
    "SK Rapid Wien": "Rapid Wien",
    "Grazer AK 1902": "Grazer AK",
    "FC Blau Weiß Linz": "FC Blau Weiß Linz",
    "WSG Tirol": "Tirol",
    "SC Rheindorf Altach": "SC Rheindorf Altach",
    "Wolfsberger AC": "Wolfsberger AC",
    "TSV Hartberg": "Hartberg",
    "LASK": "LASK Linz",
    "SV Ried": "Ried",
}

class Command(BaseCommand):
    help = "Faz o scraping das partidas da Áustria (SofaScore) de forma invisível via curl_cffi"

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
            help='ID da temporada no SofaScore (ex: 52524 para 23/24)'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Ano de término da temporada para o banco de dados (ex: 2024)'
        )

    def handle(self, *args, **kwargs):
        in_season_id = kwargs.get('season_id')
        in_year = kwargs.get('year')
        
        season_id = in_season_id if in_season_id else DEFAULT_SEASON_ID
        season_year = in_year if in_year else DEFAULT_YEAR

        self.stdout.write(self.style.SUCCESS(f"Iniciando importação do SofaScore (Áustria) para a Temporada {season_year} (Sofa_ID: {season_id})..."))

        # 1. Pegar/Criar a Liga e a Temporada
        league, _ = League.objects.get_or_create(
            name="Bundesliga",
            country="Austria",
            defaults={
                "division": 1,
                "soccerstats_slug": "austria" # To align with previous scraping logic
            }
        )
        season_qs = Season.objects.filter(year=season_year)
        if season_qs.exists():
            season = season_qs.first()
        else:
            season = Season.objects.create(year=season_year)

        # 2. Obter Teams (Standings é um bom lugar para puxar os IDs dos times da temporada)
        self.stdout.write("Buscando times da temporada...")
        standings_url = f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{season_id}/standings/total"
        standings_data = self.fetch_api(standings_url)
        
        teams_map = {} # SofaScore ID -> Team Object
        tournaments_to_scrape = [(TOURNAMENT_ID, "Regular Season")] # List of (id, label)

        if standings_data and 'standings' in standings_data:
            for standings_group in standings_data['standings']:
                group_name = standings_group.get('name', 'League')
                self.stdout.write(f"Processando grupo de classificação: {group_name}")
                
                # Coletar sub-tournaments para os Playoffs (Championship/Relegation)
                sub_tournament_id = standings_group.get('tournament', {}).get('id')
                if sub_tournament_id and sub_tournament_id != TOURNAMENT_ID:
                    if (sub_tournament_id, group_name) not in tournaments_to_scrape:
                        tournaments_to_scrape.append((sub_tournament_id, group_name))

                standings_list = standings_group.get('rows', [])
                for row in standings_list:
                    team_data = row.get('team', {})
                    team_id = str(team_data.get('id'))
                    raw_team_name = team_data.get('name')
                    team_name = TEAM_MAPPING.get(raw_team_name, raw_team_name)
                    
                    if team_id and team_name:
                        sofa_api_id = f"sofa_{team_id}"
                        
                        # 1. Try to find team by api_id
                        team = Team.objects.filter(api_id=sofa_api_id, league=league).first()
                        
                        # 2. Se não achou por api_id, procura pelo NOME canônico
                        if not team:
                            team = Team.objects.filter(name=team_name, league=league).first()
                            if team:
                                if not team.api_id:
                                    team.api_id = sofa_api_id
                                    team.save()
                        
                        # 3. Se ainda não achou, cria novo
                        if not team:
                            team = Team.objects.create(
                                name=team_name,
                                league=league,
                                api_id=sofa_api_id
                            )
                        
                        teams_map[int(team_id)] = team
            
            self.stdout.write(self.style.SUCCESS(f"{len(teams_map)} times mapeados no total."))
        else:
            self.stdout.write(self.style.ERROR("Não foi possível carregar a tabela de times para a Áustria. Abortando."))
            return

        # 3. Obter todas as partidas (Regular + Playoffs)
        for t_id, t_label in tournaments_to_scrape:
            self.stdout.write(self.style.WARNING(f"\n>>> Raspando {t_label} (ID: {t_id})..."))
            self.scrape_tournament_matches(t_id, season_id, season, league, teams_map, t_label)

    def scrape_tournament_matches(self, tourn_id, season_id, season_obj, league_obj, teams_map, label):
        rounds_url = f"https://api.sofascore.com/api/v1/unique-tournament/{tourn_id}/season/{season_id}/rounds"
        # Fallback para torneios que não são 'unique'
        if tourn_id != TOURNAMENT_ID:
             rounds_url = f"https://api.sofascore.com/api/v1/tournament/{tourn_id}/season/{season_id}/rounds"

        rounds_data = self.fetch_api(rounds_url)
        if not rounds_data or 'rounds' not in rounds_data:
            self.stdout.write(self.style.ERROR(f"Falha ao obter rodadas para {label}."))
            return
            
        total_rounds = len(rounds_data['rounds'])
        self.stdout.write(f"O torneio {label} tem {total_rounds} rodadas.")

        matches_created = 0
        matches_updated = 0

        for round_info in rounds_data['rounds']:
            round_number = round_info['round']
            events_url = f"https://api.sofascore.com/api/v1/unique-tournament/{tourn_id}/season/{season_id}/events/round/{round_number}"
            if tourn_id != TOURNAMENT_ID:
                events_url = f"https://api.sofascore.com/api/v1/tournament/{tourn_id}/season/{season_id}/events/round/{round_number}"
                
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
                    match_status = "Scheduled"
                    if status_type == 'finished':
                        match_status = "Finished"
                    elif status_type == 'inprogress':
                        match_status = "In Play"
                    elif status_type == 'canceled':
                        match_status = "Cancelled"
                    elif status_type == 'postponed':
                        match_status = "Postponed"
                    
                    home_score = ev.get('homeScore', {}).get('current')
                    away_score = ev.get('awayScore', {}).get('current')
                    
                    home_team = teams_map.get(int(home_sofa_id))
                    away_team = teams_map.get(int(away_sofa_id))
                    
                    if not home_team or not away_team:
                        continue
                    
                    match, created = Match.objects.update_or_create(
                        api_id=match_api_id,
                        defaults={
                            "league": league_obj,
                            "season": season_obj,
                            "home_team": home_team,
                            "away_team": away_team,
                            "date": match_date,
                            "round_name": f"{label} - Round {round_number}",
                            "status": match_status,
                            "home_score": home_score,
                            "away_score": away_score,
                        }
                    )
                    if created: matches_created += 1
                    else: matches_updated += 1
        
        self.stdout.write(self.style.SUCCESS(f"{label}: {matches_created} criadas, {matches_updated} atualizadas."))

