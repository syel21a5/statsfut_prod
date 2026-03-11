import time
from curl_cffi import requests
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season
from django.db import transaction

# Default Constants for French Ligue 1 2025/2026
TOURNAMENT_ID = 34
DEFAULT_SEASON_ID = 77356
DEFAULT_YEAR = 2026

TEAM_MAPPING = {
    "Paris Saint-Germain": "PSG",
    "Paris Saint-Germain FC": "PSG",
    "AS Monaco": "Monaco",
    "AS Monaco FC": "Monaco",
    "Olympique Lyonnais": "Lyon",
    "Olympique de Marseille": "Marseille",
    "Lille OSC": "Lille",
    "Stade Rennais": "Rennes",
    "OGC Nice": "Nice",
    "RC Lens": "Lens",
    "Stade de Reims": "Reims",
    "Stade Brestois": "Brest",
    "Stade Brestois 29": "Brest",
    "Toulouse FC": "Toulouse",
    "Montpellier HSC": "Montpellier",
    "RC Strasbourg Alsace": "Strasbourg",
    "FC Nantes": "Nantes",
    "Le Havre AC": "Le Havre",
    "Angers SCO": "Angers",
    "AJ Auxerre": "Auxerre",
    "AS Saint-Étienne": "St Etienne",
}

class Command(BaseCommand):
    help = "Faz o scraping das partidas da França (Ligue 1) via SofaScore"

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
            time.sleep(1.2)
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao acessar {url}: {e}"))
            return None

    def handle(self, *args, **kwargs):
        season_year = DEFAULT_YEAR
        season_id = DEFAULT_SEASON_ID

        self.stdout.write(self.style.SUCCESS(f"Iniciando Ligue 1 (França) {season_year}..."))

        league, _ = League.objects.get_or_create(
            name="Ligue 1", country="Franca", defaults={"division": 1}
        )
        season, _ = Season.objects.get_or_create(year=season_year)

        # 1. Mapear Times
        standings_url = f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{season_id}/standings/total"
        data = self.fetch_api(standings_url)
        teams_map = {}

        if data and 'standings' in data:
            for group in data['standings']:
                for row in group.get('rows', []):
                    t_data = row.get('team', {})
                    t_id = t_data.get('id')
                    raw_name = t_data.get('name')
                    name = TEAM_MAPPING.get(raw_name, raw_name)
                    
                    team, _ = Team.objects.get_or_create(name=name, league=league)
                    teams_map[int(t_id)] = team
        
        # 2. Partidas
        rounds_url = f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{season_id}/rounds"
        r_data = self.fetch_api(rounds_url)
        if r_data and 'rounds' in r_data:
            from django.core.management import call_command
            for r_info in r_data['rounds']:
                r_num = r_info['round']
                events_url = f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{season_id}/events/round/{r_num}"
                ev_data = self.fetch_api(events_url)
                if ev_data and 'events' in ev_data:
                    with transaction.atomic():
                        for ev in ev_data['events']:
                            fid = str(ev.get('id'))
                            h_id = ev.get('homeTeam', {}).get('id')
                            a_id = ev.get('awayTeam', {}).get('id')
                            
                            h_team = teams_map.get(int(h_id))
                            a_team = teams_map.get(int(a_id))
                            if not h_team or not a_team: continue

                            start_ts = ev.get('startTimestamp')
                            match_date = datetime.fromtimestamp(start_ts, tz=timezone.utc)
                            
                            status_type = ev.get('status', {}).get('type')
                            status = "Finished" if status_type == 'finished' else "Scheduled"
                            if status_type == 'inprogress': status = "In Play"
                            
                            Match.objects.update_or_create(
                                api_id=f"sofa_{fid}",
                                defaults={
                                    "league": league, "season": season,
                                    "home_team": h_team, "away_team": a_team,
                                    "date": match_date, "status": status,
                                    "home_score": ev.get('homeScore', {}).get('current'),
                                    "away_score": ev.get('awayScore', {}).get('current'),
                                }
                            )
        
            call_command('recalculate_standings', league_name='Ligue 1', country='Franca', smart=True)
            self.stdout.write(self.style.SUCCESS("França atualizada com sucesso!"))
