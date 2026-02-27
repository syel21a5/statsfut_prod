import requests
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from matches.models import Match, Team, League, Season, APIUsage
from matches.utils_odds_api import resolve_team
import os
from datetime import datetime
import pytz

class Command(BaseCommand):
    help = 'Import upcoming fixtures from The Odds API (Credit safe)'

    # Configuração de Ligas Suportadas
    LEAGUE_CONFIG = {
        'soccer_argentina_primera_division': {
            'env_key': 'ODDS_API_KEY_ARGENTINA_UPCOMING',
            'db_name': 'Liga Profesional',
            'country': 'Argentina'
        },
        'soccer_brazil_campeonato': {
            'env_key': 'ODDS_API_KEY_BRAZIL_UPCOMING',
            'db_name': 'Brasileirão',
            'country': 'Brasil'
        },
        'soccer_epl': {
            'env_key': 'ODDS_API_KEY_ENGLAND_UPCOMING',
            'db_name': 'Premier League',
            'country': 'Inglaterra'
        },
        'soccer_austria_bundesliga': {
            'env_key': 'ODDS_API_KEY_AUSTRIA_UPCOMING',
            'db_name': 'Bundesliga',
            'country': 'Austria'
        },
        'soccer_australia_aleague': {
            'env_key': 'ODDS_API_KEY_AUSTRALIA_UPCOMING',
            'db_name': 'A League',
            'country': 'Australia'
        },
        'soccer_belgium_first_div': {
            'env_key': 'ODDS_API_KEY_BELGIUM_UPCOMING',
            'db_name': 'Pro League',
            'country': 'Belgica'
        },
        'soccer_switzerland_superleague': {
            'env_key': 'ODDS_API_KEY_SWITZERLAND_UPCOMING',
            'db_name': 'Super League',
            'country': 'Suica'
        },
        'soccer_denmark_superliga': {
            'env_key': 'ODDS_API_KEY_DENMARK_UPCOMING',
            'db_name': 'Superliga',
            'country': 'Dinamarca'
        },
        'soccer_czech_first_league': {
            'env_key': 'ODDS_API_KEY_CZECH_UPCOMING',
            'db_name': 'First League',
            'country': 'Republica Tcheca'
        }
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--league',
            type=str,
            help='Specific league key (e.g., soccer_argentina_primera_division) or ALL',
            default='soccer_argentina_primera_division'
        )
        parser.add_argument(
            '--check-credits',
            action='store_true',
            help='Check credits and exit'
        )

    def handle(self, *args, **options):
        league_arg = options['league']
        
        if league_arg == 'ALL':
            leagues_to_process = self.LEAGUE_CONFIG.keys()
            self.stdout.write(self.style.SUCCESS(f"Starting batch update for ALL {len(leagues_to_process)} leagues..."))
        else:
            leagues_to_process = [league_arg]

        for league_key in leagues_to_process:
            self.process_league(league_key, options['check_credits'])

    def process_league(self, league_key, check_credits):
        # 1. Carregar configuração da liga
        config = self.LEAGUE_CONFIG.get(league_key)
        if not config:
            self.stdout.write(self.style.ERROR(f"Liga '{league_key}' não configurada no script."))
            self.stdout.write(f"Ligas disponíveis: {', '.join(self.LEAGUE_CONFIG.keys())}")
            return

        api_key_env = config['env_key']
        api_key = os.getenv(api_key_env)
        
        if not api_key:
            self.stdout.write(self.style.ERROR(f"Chave {api_key_env} não encontrada no .env para {league_key}"))
            return

        base_url = "https://api.the-odds-api.com/v4"
        
        # 2. Construir URL
        url = f"{base_url}/sports/{league_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h"
        
        if check_credits:
            try:
                resp = requests.get(f"{base_url}/sports/?apiKey={api_key}")
                resp.raise_for_status()
                remaining = int(resp.headers.get('x-requests-remaining', 0))
                used = int(resp.headers.get('x-requests-used', 0))
                self.stdout.write(f"API Credits ({config['country']}): Used {used}, Remaining {remaining}")
                return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to check credits for {league_key}: {e}"))
                return

        self.stdout.write(f"Fetching fixtures for {league_key} ({config['country']})...")
        
        try:
            response = requests.get(url)
            
            # Check credits
            remaining = int(response.headers.get('x-requests-remaining', 0))
            used = int(response.headers.get('x-requests-used', 0))
            
            # Log usage
            self.stdout.write(f"Credits used: {used}, Remaining: {remaining}")
            
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Error fetching data: {response.text}"))
                return

            data = response.json()
            
            # Process fixtures
            count_created = 0
            count_updated = 0
            
            # Get League object
            try:
                league_obj = League.objects.get(name=config['db_name'], country=config['country'])
            except League.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"League {config['db_name']} ({config['country']}) not found in DB"))
                return

            current_year = timezone.now().year
            # Tentar pegar season atual ou proxima
            season, _ = Season.objects.get_or_create(year=current_year)

            for item in data:
                home_team = item['home_team']
                away_team = item['away_team']
                commence_time = item['commence_time'] # ISO format
                
                # Parse date
                match_date = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                
                # Resolve Teams
                ht_obj = resolve_team(home_team, league_obj)
                at_obj = resolve_team(away_team, league_obj)
                
                if not ht_obj or not at_obj:
                    self.stdout.write(self.style.WARNING(f"Skipping {home_team} vs {away_team} (Team not resolved)"))
                    continue
                
                # Get Odds
                avg_home_odd = None
                avg_draw_odd = None
                avg_away_odd = None
                
                # Extract average odds from bookmakers
                bookmakers = item.get('bookmakers', [])
                if bookmakers:
                    # Simple strategy: take first available or average
                    # Let's take the first one for simplicity or specific bookmaker if needed
                    # Or average them
                    h_odds = []
                    d_odds = []
                    a_odds = []
                    
                    for book in bookmakers:
                        for market in book.get('markets', []):
                            if market['key'] == 'h2h':
                                for outcome in market['outcomes']:
                                    if outcome['name'] == home_team:
                                        h_odds.append(outcome['price'])
                                    elif outcome['name'] == away_team:
                                        a_odds.append(outcome['price'])
                                    elif outcome['name'] == 'Draw':
                                        d_odds.append(outcome['price'])
                    
                    if h_odds: avg_home_odd = sum(h_odds) / len(h_odds)
                    if d_odds: avg_draw_odd = sum(d_odds) / len(d_odds)
                    if a_odds: avg_away_odd = sum(a_odds) / len(a_odds)

                # Update or Create Match
                # We identify match by teams and date (approx)
                # Or try to find existing match in a window of 24h
                
                match = Match.objects.filter(
                    league=league_obj,
                    home_team=ht_obj,
                    away_team=at_obj,
                    date__date=match_date.date()
                ).first()

                if match:
                    # Update odds
                    match.home_team_win_odds = avg_home_odd
                    match.draw_odds = avg_draw_odd
                    match.away_team_win_odds = avg_away_odd
                    # Ensure status is Scheduled if it was not Finished
                    if match.status not in ['Finished', 'Live', 'Postponed']:
                         match.status = 'Scheduled'
                         match.date = match_date # Update exact time
                    match.save()
                    count_updated += 1
                else:
                    # Create new match
                    Match.objects.create(
                        league=league_obj,
                        home_team=ht_obj,
                        away_team=at_obj,
                        date=match_date,
                        season=season,
                        status='Scheduled',
                        home_team_win_odds=avg_home_odd,
                        draw_odds=avg_draw_odd,
                        away_team_win_odds=avg_away_odd
                    )
                    count_created += 1
            
            self.stdout.write(self.style.SUCCESS(f"[{league_key}] Processed. Created: {count_created}, Updated: {count_updated}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in {league_key}: {e}"))
            try:
                # Log usage even on error if possible
                if 'remaining' in locals():
                    APIUsage.objects.update_or_create(
                        api_name=f"The Odds API (Upcoming - {config['country']})",
                        defaults={'credits_remaining': remaining, 'credits_used': used}
                    )
            except Exception:
                pass
