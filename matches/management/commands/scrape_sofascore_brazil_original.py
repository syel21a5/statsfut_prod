import time
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import Match, Team, League, Season, Goal
from curl_cffi import requests
from datetime import datetime
import json

class Command(BaseCommand):
    help = 'Scrape detailed stats (corners, cards, etc.) from Sofascore for Brasileirão 2026'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Sofascore scraper for Brasileirão 2026..."))
        
        # Configuration
        SEASON_YEAR = 2026
        SEASON_ID = 87678  # 2026 Sofascore ID
        TOURNAMENT_ID = 325 # Brasileirão Serie A
        LEAGUE_NAME = "Brasileirão" # Name in our DB
        
        # Get League object
        try:
            league = League.objects.get(name=LEAGUE_NAME)
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"League '{LEAGUE_NAME}' not found in DB."))
            return

        # Get Season object
        season, _ = Season.objects.get_or_create(year=SEASON_YEAR)

        # Setup requests session with browser impersonation
        self.session = requests.Session()
        self.session.headers = {
            'Referer': 'https://www.sofascore.com/',
            'Origin': 'https://www.sofascore.com',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }

        # Iterate through rounds (1 to 38)
        for round_num in range(1, 39):
            self.stdout.write(f"Processing Round {round_num}...")
            self.process_round(round_num, SEASON_ID, TOURNAMENT_ID, league, season)
            
            # Sleep to avoid rate limiting
            time.sleep(random.uniform(2, 5))

    def process_round(self, round_num, season_id, tournament_id, league, season):
        url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{round_num}"
        
        try:
            response = self.session.get(url, impersonate="chrome120", timeout=15)
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Failed to fetch round {round_num}: {response.status_code}"))
                return

            data = response.json()
            events = data.get('events', [])
            
            for event in events:
                self.process_event(event, league, season)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing round {round_num}: {str(e)}"))

    def process_event(self, event, league, season):
        # Basic Info
        event_id = event.get('id')
        home_name = event.get('homeTeam', {}).get('name')
        away_name = event.get('awayTeam', {}).get('name')
        start_timestamp = event.get('startTimestamp')
        status_code = event.get('status', {}).get('code') # 100=Ended, 0=NotStarted?
        
        # Convert timestamp to datetime
        match_date = datetime.fromtimestamp(start_timestamp, tz=timezone.get_current_timezone())
        
        # Resolve Teams
        home_team = self.resolve_team(home_name, league)
        away_team = self.resolve_team(away_name, league)
        
        if not home_team or not away_team:
            self.stdout.write(self.style.WARNING(f"Skipping match {home_name} vs {away_name} (Team not found)"))
            return

        # Create or Update Match
        match, created = Match.objects.get_or_create(
            league=league,
            home_team=home_team,
            away_team=away_team,
            season=season, # Pass Season object
            defaults={'date': match_date}
        )
        
        # Update basic scores if finished
        if status_code == 100: # Finished
            home_score_data = event.get('homeScore', {})
            away_score_data = event.get('awayScore', {})
            
            match.home_score = home_score_data.get('current')
            match.away_score = away_score_data.get('current')
            match.ht_home_score = home_score_data.get('period1')
            match.ht_away_score = away_score_data.get('period1')
            match.status = "Finished"
            match.api_id = str(event_id)
            
            # Fetch Detailed Stats
            self.fetch_match_stats(event_id, match)
            
            # Fetch Incidents (Goals)
            self.fetch_incidents(event_id, match)
        else:
            match.status = "Scheduled"
            match.date = match_date # Update date/time just in case
            
        match.save()
        action = "Created" if created else "Updated"
        self.stdout.write(f"  {action}: {home_team} vs {away_team} ({match.status})")

    def fetch_match_stats(self, event_id, match):
        url = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
        try:
            response = requests.get(url, impersonate="chrome110", timeout=10)
            if response.status_code == 200:
                data = response.json()
                stats_groups = data.get('statistics', [])
                if not stats_groups:
                    return

                # Iterate through groups (usually only one "ALL" period)
                for group in stats_groups[0].get('groups', []):
                    items = group.get('statisticsItems', [])
                    for item in items:
                        name = item.get('name')
                        home_val = item.get('home')
                        away_val = item.get('away')
                        
                        # Map to our model fields
                        if name == "Corner kicks":
                            match.home_corners = self.safe_int(home_val)
                            match.away_corners = self.safe_int(away_val)
                        elif name == "Fouls":
                            match.home_fouls = self.safe_int(home_val)
                            match.away_fouls = self.safe_int(away_val)
                        elif name == "Yellow cards":
                            match.home_yellow = self.safe_int(home_val)
                            match.away_yellow = self.safe_int(away_val)
                        elif name == "Red cards":
                            match.home_red = self.safe_int(home_val)
                            match.away_red = self.safe_int(away_val)
                        elif name == "Total shots":
                            match.home_shots = self.safe_int(home_val)
                            match.away_shots = self.safe_int(away_val)
                        elif name == "Shots on target":
                            match.home_shots_on_target = self.safe_int(home_val)
                            match.away_shots_on_target = self.safe_int(away_val)
                
                match.save()
                # self.stdout.write(f"    Stats updated for {match}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Error fetching stats for event {event_id}: {e}"))

    def fetch_incidents(self, event_id, match):
        url = f"https://api.sofascore.com/api/v1/event/{event_id}/incidents"
        try:
            response = requests.get(url, impersonate="chrome110", timeout=10)
            if response.status_code == 200:
                data = response.json()
                incidents = data.get('incidents', [])
                
                # Clear existing goals to avoid duplicates
                match.goals.all().delete()
                
                for inc in incidents:
                    if inc.get('incidentType') == 'goal':
                        is_home = inc.get('isHome', False)
                        team = match.home_team if is_home else match.away_team
                        
                        # Extract player info
                        player_name = inc.get('player', {}).get('name', 'Unknown')
                        minute = inc.get('time', 0)
                        
                        # Check for own goal or penalty
                        is_own = inc.get('incidentClass') == 'ownGoal'
                        is_pen = inc.get('incidentClass') == 'penalty'
                        
                        # Create Goal
                        Goal.objects.create(
                            match=match,
                            team=team,
                            player_name=player_name,
                            minute=minute,
                            is_own_goal=is_own,
                            is_penalty=is_pen
                        )
                        # self.stdout.write(f"    Goal: {player_name} ({minute}')")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Error fetching incidents for event {event_id}: {e}"))

    def resolve_team(self, name, league):
        team = Team.objects.filter(name__iexact=name, league=league).first()
        if team:
            return team

        aliases = {
            "Atlético Mineiro": "Atletico-MG",
            "Athletico": "Athletico-PR",
            "São Paulo": "Sao Paulo",
            "Grêmio": "Gremio",
            "Vitória": "Vitoria",
            "Criciúma": "Criciuma",
            "Goiás": "Goias",
            "América Mineiro": "America-MG",
            "Ceará": "Ceara",
            "Sport Recife": "Sport Recife",
            "Red Bull Bragantino": "Bragantino",
            "Vasco da Gama": "Vasco",
            "Botafogo": "Botafogo",
            "Atlético Goianiense": "Atletico-GO",
            "Cuiabá": "Cuiaba",
            "Avaí": "Avai",
            "Flamengo": "Flamengo",
            "Fluminense": "Fluminense",
            "Palmeiras": "Palmeiras",
            "Santos": "Santos",
            "Corinthians": "Corinthians",
            "Internacional": "Internacional",
            "Bahia": "Bahia",
            "Fortaleza": "Fortaleza",
            "Juventude": "Juventude",
            "Cruzeiro": "Cruzeiro",
            "Mirassol": "Mirassol",
            "Chapecoense": "Chapecoense",
        }

        mapped_name = aliases.get(name)
        if mapped_name:
            team = Team.objects.filter(name__iexact=mapped_name, league=league).first()
            if team:
                return team

        return None

    def safe_int(self, val):
        try:
            return int(val)
        except:
            return 0
