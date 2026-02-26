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
        }
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--league',
            type=str,
            help='Specific league key (e.g., soccer_argentina_primera_division)',
            default='soccer_argentina_primera_division'
        )
        parser.add_argument(
            '--check-credits',
            action='store_true',
            help='Check credits and exit'
        )

    def handle(self, *args, **options):
        league_key = options['league']
        
        # 1. Carregar configuração da liga
        config = self.LEAGUE_CONFIG.get(league_key)
        if not config:
            self.stdout.write(self.style.ERROR(f"Liga '{league_key}' não configurada no script."))
            self.stdout.write(f"Ligas disponíveis: {', '.join(self.LEAGUE_CONFIG.keys())}")
            return

        api_key_env = config['env_key']
        api_key = os.getenv(api_key_env)
        
        if not api_key:
            self.stdout.write(self.style.ERROR(f"Chave {api_key_env} não encontrada no .env"))
            return

        base_url = "https://api.the-odds-api.com/v4"
        
        # 2. Construir URL
        url = f"{base_url}/sports/{league_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h"
        
        if options['check_credits']:
            try:
                resp = requests.get(f"{base_url}/sports/?apiKey={api_key}")
                resp.raise_for_status()
                remaining = int(resp.headers.get('x-requests-remaining', 0))
                used = int(resp.headers.get('x-requests-used', 0))
                self.stdout.write(f"API Credits ({config['country']}): Used {used}, Remaining {remaining}")
                return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to check credits: {e}"))
                return

        self.stdout.write(f"Fetching fixtures for {league_key} ({config['country']})...")
        
        try:
            response = requests.get(url)
            
            # Check credits
            remaining = int(response.headers.get('x-requests-remaining', 0))
            used = int(response.headers.get('x-requests-used', 0))
            
            # Log usage
            try:
                APIUsage.objects.update_or_create(
                    api_name=f"The Odds API (Upcoming - {config['country']})",
                    defaults={'credits_remaining': remaining, 'credits_used': used}
                )
            except Exception as db_e:
                self.stdout.write(self.style.WARNING(f"Failed to log API usage: {db_e}"))

            self.stdout.write(f"API Credits: Used {used}, Remaining {remaining}")
            
            if remaining < 50:
                 self.stdout.write(self.style.WARNING("Low credits! Consider pausing updates."))

            response.raise_for_status()
            matches_data = response.json()
            self.stdout.write(self.style.SUCCESS(f"Fetched {len(matches_data)} matches."))
            
            # 3. Identificar Liga no Banco
            # Tenta busca exata primeiro
            league_obj = League.objects.filter(
                name__icontains=config['db_name'], 
                country__icontains=config['country']
            ).first()
            
            if not league_obj:
                # Tenta busca mais ampla
                league_obj = League.objects.filter(name__icontains=config['db_name']).first()

            if not league_obj:
                self.stdout.write(self.style.ERROR(f"Liga '{config['db_name']}' ({config['country']}) não encontrada no DB."))
                return

            # Get or Create Season 2026
            current_year = 2026 
            season_obj, _ = Season.objects.get_or_create(year=current_year)

            updates = 0
            creates = 0

            for m in matches_data:
                home_name = m['home_team']
                away_name = m['away_team']
                commence_time_str = m['commence_time'] # ISO format e.g. 2024-03-30T15:00:00Z
                
                # Parse date
                match_date = datetime.strptime(commence_time_str, "%Y-%m-%dT%H:%M:%SZ")
                match_date = pytz.utc.localize(match_date)
                
                # Resolve Teams
                home_team_obj = resolve_team(home_name, league_obj)
                away_team_obj = resolve_team(away_name, league_obj)
                
                if not home_team_obj or not away_team_obj:
                    # Opcional: Criar times se não existirem (CUIDADO: pode duplicar se nome for diferente)
                    # Por enquanto, apenas loga e pula para evitar sujeira
                    self.stdout.write(f"Skipping unknown teams: {home_name} vs {away_name}")
                    continue
                
                # Check if match exists (using teams and approximate date to avoid duplicates if time changes slightly)
                # Date range: +/- 24 hours
                start_window = match_date - timezone.timedelta(hours=24)
                end_window = match_date + timezone.timedelta(hours=24)
                
                match = Match.objects.filter(
                    league=league_obj,
                    home_team=home_team_obj,
                    away_team=away_team_obj,
                    date__range=(start_window, end_window)
                ).first()
                
                if match:
                    # Update time if needed
                    time_diff = abs((match.date - match_date).total_seconds())
                    if time_diff > 3600: # If changed by more than 1 hour
                        match.date = match_date
                        match.status = 'Scheduled'
                        match.save()
                        updates += 1
                        self.stdout.write(f"Updated Time: {home_team_obj} vs {away_team_obj}")
                else:
                    Match.objects.create(
                        league=league_obj,
                        season=season_obj,
                        home_team=home_team_obj,
                        away_team=away_team_obj,
                        date=match_date,
                        status='Scheduled'
                    )
                    creates += 1
                    self.stdout.write(f"Created: {home_team_obj} vs {away_team_obj} at {match_date}")
            
            self.stdout.write(self.style.SUCCESS(f"Done. Created: {creates}, Updated: {updates}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching data: {e}"))
