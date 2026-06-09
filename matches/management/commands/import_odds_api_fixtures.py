import requests
import logging
from django.core.management import call_command
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
        # REMOVIDO PARA SOFASCORE:
        # 'soccer_austria_bundesliga': {
        #     'env_key': 'ODDS_API_KEY_AUSTRIA_UPCOMING',
        #     'db_name': 'Bundesliga',
        #     'country': 'Austria'
        # },
        # 'soccer_australia_aleague': {
        #     'env_key': 'ODDS_API_KEY_AUSTRALIA_UPCOMING',
        #     'db_name': 'A-League Men',
        #     'country': 'Australia'
        # },
        # 'soccer_belgium_first_div': {
        #     'env_key': 'ODDS_API_KEY_BELGIUM_UPCOMING',
        #     'db_name': 'Pro League',
        #     'country': 'Belgica'
        # },
        # 'soccer_switzerland_superleague': {
        #     'env_key': 'ODDS_API_KEY_SWITZERLAND_UPCOMING',
        #     'db_name': 'Super League',
        #     'country': 'Suica'
        # },
        'soccer_denmark_superliga': {
            'env_key': 'ODDS_API_KEY_DENMARK_UPCOMING',
            'db_name': 'Superliga',
            'country': 'Dinamarca'
        },
        'soccer_germany_bundesliga': {
            'env_key': 'ODDS_API_KEY_GERMANY_UPCOMING',
            'db_name': 'Bundesliga',
            'country': 'Alemanha'
        },
        'soccer_france_ligue_one': {
            'env_key': 'ODDS_API_KEY_FRANCE_UPCOMING',
            'db_name': 'Ligue 1',
            'country': 'Franca'
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
        parser.add_argument(
            '--scores',
            action='store_true',
            help='Fetch recent scores (results) instead of upcoming odds'
        )

        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Number of days to look back for scores (default: 3)'
        )

    def handle(self, *args, **options):
        league_arg = options['league']
        
        if league_arg == 'ALL':
            leagues_to_process = self.LEAGUE_CONFIG.keys()
            self.stdout.write(self.style.SUCCESS(f"Starting batch update for ALL {len(leagues_to_process)} leagues..."))
        else:
            leagues_to_process = [league_arg]

        for league_key in leagues_to_process:
            if options['scores']:
                self.process_scores(league_key)
            else:
                self.process_league(league_key, options['check_credits'])

    def _get_api_keys_pool(self, primary_env_key):
        """
        Retorna uma lista de chaves da API ordenadas, começando pela chave primária da liga,
        seguida por todas as outras chaves disponíveis no pool do .env.
        """
        keys_pool = []
        primary = os.getenv(primary_env_key)
        if primary:
            keys_pool.append((primary_env_key, primary))
        else:
            primary_fallback = getattr(settings, primary_env_key, None)
            if primary_fallback:
                keys_pool.append((primary_env_key, primary_fallback))
            
        env_vars = [
            'ODDS_API_KEY_ARGENTINA_UPCOMING',
            'ODDS_API_KEY_AUSTRIA_UPCOMING',
            'ODDS_API_KEY_AUSTRALIA_UPCOMING',
            'ODDS_API_KEY_BELGIUM_UPCOMING',
            'ODDS_API_KEY_BRAZIL_UPCOMING',
            'ODDS_API_KEY_SWITZERLAND_UPCOMING',
            'ODDS_API_KEY_GERMANY_UPCOMING',
            'ODDS_API_KEY_FRANCE_UPCOMING',
            'ODDS_API_KEY_ENGLAND_UPCOMING',
            'ODDS_API_KEY_DENMARK_UPCOMING',
            'ODDS_API_KEY_BRAZIL_LIVE_2',
            'ODDS_API_KEY_BRAZIL_LIVE_3',
            'ODDS_API_KEY_ENGLAND_LIVE_1',
            'ODDS_API_KEY_ENGLAND_LIVE_2',
            'ODDS_API_KEY_ENGLAND_LIVE_3',
            'ODDS_API_KEY_AUSTRIA_LIVE_1',
            'ODDS_API_KEY_AUSTRIA_LIVE_2',
            'ODDS_API_KEY_AUSTRIA_LIVE_3',
            'ODDS_API_KEY_AUSTRALIA_LIVE_1',
            'ODDS_API_KEY_AUSTRALIA_LIVE_2',
            'ODDS_API_KEY_AUSTRALIA_LIVE_3',
        ]
        
        for var in env_vars:
            if var != primary_env_key:
                val = os.getenv(var)
                if val and val not in [k[1] for k in keys_pool]:
                    keys_pool.append((var, val))
                    
        return keys_pool

    def process_scores(self, league_key, days=3):
        """Fetch recent scores for a league"""
        config = self.LEAGUE_CONFIG.get(league_key)
        if not config:
            self.stdout.write(self.style.ERROR(f"Liga '{league_key}' não configurada."))
            return

        api_key_env = config['env_key']
        keys_pool = self._get_api_keys_pool(api_key_env)
        if not keys_pool:
            self.stdout.write(self.style.ERROR(f"Chave {api_key_env} não encontrada."))
            return

        base_url = "https://api.the-odds-api.com/v4"
        response = None
        data = None

        self.stdout.write(f"Fetching SCORES for {league_key} ({config['country']}) - Last {days} days...")

        for key_name, key_val in keys_pool:
            url = f"{base_url}/sports/{league_key}/scores/?apiKey={key_val}&daysFrom={days}"
            self.stdout.write(f"Trying key {key_name} for scores...")
            try:
                resp = requests.get(url)
                remaining = int(resp.headers.get('x-requests-remaining', 0))
                used = int(resp.headers.get('x-requests-used', 0))
                
                try:
                    APIUsage.objects.update_or_create(
                        api_name=f"The Odds API ({key_name})",
                        defaults={'credits_remaining': remaining, 'credits_used': used}
                    )
                except Exception:
                    pass

                if resp.status_code == 200:
                    response = resp
                    data = resp.json()
                    self.stdout.write(self.style.SUCCESS(f"Success using key {key_name}! Credits remaining: {remaining}"))
                    break
                else:
                    self.stdout.write(self.style.WARNING(f"Key {key_name} returned status {resp.status_code}, checking next..."))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed with key {key_name}: {e}"))

        if not response:
            self.stdout.write(self.style.ERROR("All keys in the pool failed to fetch scores."))
            return

        try:
            try:
                league_obj = League.objects.get(name=config['db_name'], country=config['country'])
            except League.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"League {config['db_name']} not found"))
                return

            count_updated = 0
            count_created = 0
            current_year = timezone.now().year
            season, _ = Season.objects.get_or_create(year=current_year)

            for item in data:
                if not item.get('completed', False):
                    continue

                home_team = item['home_team']
                away_team = item['away_team']
                commence_time = item['commence_time']
                scores = item.get('scores', [])

                if not scores:
                    continue

                match_date = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                ht_obj = resolve_team(home_team, league_obj)
                at_obj = resolve_team(away_team, league_obj)

                if not ht_obj or not at_obj:
                    continue

                home_score = None
                away_score = None
                for s in scores:
                    if s['name'] == home_team:
                        home_score = int(s['score'])
                    elif s['name'] == away_team:
                        away_score = int(s['score'])

                if home_score is None or away_score is None:
                    continue

                match = Match.objects.filter(
                    league=league_obj,
                    home_team=ht_obj,
                    away_team=at_obj,
                    date__date=match_date.date()
                ).first()
                
                if match:
                    if match.status != 'Finished':
                        match.status = 'Finished'
                        match.home_score = home_score
                        match.away_score = away_score
                        match.save()
                        self.stdout.write(self.style.SUCCESS(f"Updated Match Result: {ht_obj.name} {home_score}-{away_score} {at_obj.name}"))
                        count_updated += 1
                else:
                    Match.objects.create(
                        league=league_obj,
                        home_team=ht_obj,
                        away_team=at_obj,
                        date=match_date,
                        season=season,
                        status='Finished',
                        home_score=home_score,
                        away_score=away_score
                    )
                    self.stdout.write(self.style.SUCCESS(f"Created Match Result: {ht_obj.name} {home_score}-{away_score} {at_obj.name}"))
                    count_created += 1

            self.stdout.write(self.style.SUCCESS(f"[{league_key}] Scores Processed. Created: {count_created}, Updated: {count_updated}"))

            if count_created > 0 or count_updated > 0:
                self.stdout.write(f"Automatically recalculating standings for {config['db_name']}...")
                try:
                    call_command('recalculate_standings', league_name=config['db_name'], country=config['country'])
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to recalculate standings: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in process_scores for {league_key}: {e}"))

    def process_league(self, league_key, check_credits):
        config = self.LEAGUE_CONFIG.get(league_key)
        if not config:
            self.stdout.write(self.style.ERROR(f"Liga '{league_key}' não configurada no script."))
            return

        api_key_env = config['env_key']
        keys_pool = self._get_api_keys_pool(api_key_env)
        if not keys_pool:
            self.stdout.write(self.style.ERROR(f"Chave {api_key_env} não encontrada."))
            return

        base_url = "https://api.the-odds-api.com/v4"
        
        if check_credits:
            for key_name, key_val in keys_pool:
                try:
                    resp = requests.get(f"{base_url}/sports/?apiKey={key_val}")
                    resp.raise_for_status()
                    remaining = int(resp.headers.get('x-requests-remaining', 0))
                    used = int(resp.headers.get('x-requests-used', 0))
                    self.stdout.write(f"API Credits using {key_name} ({config['country']}): Used {used}, Remaining {remaining}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to check credits for key {key_name}: {e}"))
            return

        self.stdout.write(f"Fetching fixtures for {league_key} ({config['country']})...")
        response = None
        data = None

        for key_name, key_val in keys_pool:
            url = f"{base_url}/sports/{league_key}/odds/?apiKey={key_val}&regions=eu&markets=h2h,totals"
            self.stdout.write(f"Trying key {key_name}...")
            try:
                resp = requests.get(url)
                remaining = int(resp.headers.get('x-requests-remaining', 0))
                used = int(resp.headers.get('x-requests-used', 0))
                
                try:
                    APIUsage.objects.update_or_create(
                        api_name=f"The Odds API ({key_name})",
                        defaults={'credits_remaining': remaining, 'credits_used': used}
                    )
                except Exception:
                    pass

                if resp.status_code == 200:
                    response = resp
                    data = resp.json()
                    self.stdout.write(self.style.SUCCESS(f"Success using key {key_name}! Credits remaining: {remaining}"))
                    break
                else:
                    self.stdout.write(self.style.WARNING(f"Key {key_name} returned status {resp.status_code}, checking next..."))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed with key {key_name}: {e}"))

        if not response:
            self.stdout.write(self.style.ERROR(f"All keys in the pool failed to fetch odds for {league_key}."))
            return

        try:
            count_created = 0
            count_updated = 0
            try:
                league_obj = League.objects.get(name=config['db_name'], country=config['country'])
            except League.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"League {config['db_name']} ({config['country']}) not found in DB"))
                return

            current_year = timezone.now().year
            season, _ = Season.objects.get_or_create(year=current_year)

            for item in data:
                home_team = item['home_team']
                away_team = item['away_team']
                commence_time = item['commence_time']
                
                match_date = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                ht_obj = resolve_team(home_team, league_obj)
                at_obj = resolve_team(away_team, league_obj)
                
                if not ht_obj or not at_obj:
                    continue
                
                avg_home_odd = None
                avg_draw_odd = None
                avg_away_odd = None
                avg_over25_odd = None
                avg_under25_odd = None
                
                bookmakers = item.get('bookmakers', [])
                if bookmakers:
                    h_odds = []
                    d_odds = []
                    a_odds = []
                    o25_odds = []
                    u25_odds = []
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
                            elif market['key'] == 'totals':
                                for outcome in market['outcomes']:
                                    if outcome.get('point') == 2.5:
                                        if outcome['name'] == 'Over':
                                            o25_odds.append(outcome['price'])
                                        elif outcome['name'] == 'Under':
                                            u25_odds.append(outcome['price'])
                    if h_odds: avg_home_odd = sum(h_odds) / len(h_odds)
                    if d_odds: avg_draw_odd = sum(d_odds) / len(d_odds)
                    if a_odds: avg_away_odd = sum(a_odds) / len(a_odds)
                    if o25_odds: avg_over25_odd = sum(o25_odds) / len(o25_odds)
                    if u25_odds: avg_under25_odd = sum(u25_odds) / len(u25_odds)

                start_window = match_date - timezone.timedelta(hours=24)
                end_window = match_date + timezone.timedelta(hours=24)
                
                match = Match.objects.filter(
                    league=league_obj,
                    home_team=ht_obj,
                    away_team=at_obj,
                    date__range=(start_window, end_window)
                ).first()

                if match:
                    match.home_team_win_odds = avg_home_odd
                    match.draw_odds = avg_draw_odd
                    match.away_team_win_odds = avg_away_odd
                    match.over_25_odds = avg_over25_odd
                    match.under_25_odds = avg_under25_odd
                    if match.status not in ['Finished', 'Live', 'Postponed']:
                         match.status = 'Scheduled'
                         match.date = match_date
                    match.save()
                    count_updated += 1
                else:
                    Match.objects.create(
                        league=league_obj,
                        home_team=ht_obj,
                        away_team=at_obj,
                        date=match_date,
                        season=season,
                        status='Scheduled',
                        home_team_win_odds=avg_home_odd,
                        draw_odds=avg_draw_odd,
                        away_team_win_odds=avg_away_odd,
                        over_25_odds=avg_over25_odd,
                        under_25_odds=avg_under25_odd
                    )
                    count_created += 1
            
            self.stdout.write(self.style.SUCCESS(f"[{league_key}] Processed. Created: {count_created}, Updated: {count_updated}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in {league_key}: {e}"))
