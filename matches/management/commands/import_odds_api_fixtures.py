import requests
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from matches.models import Match, Team, League, Season, APIUsage
import os
from datetime import datetime
import pytz

class Command(BaseCommand):
    help = 'Import upcoming fixtures from The Odds API (Credit safe)'

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
        api_key = os.getenv('ODDS_API_KEY_ARGENTINA_UPCOMING')
        if not api_key:
            self.stdout.write(self.style.ERROR("ODDS_API_KEY_ARGENTINA_UPCOMING not found in .env"))
            return

        base_url = "https://api.the-odds-api.com/v4"
        league_key = options['league']
        
        # 1. Fetch Odds (Matches) directly - response headers contain credit info
        # regions=eu (doesn't matter for fixtures, but required), markets=h2h (standard)
        url = f"{base_url}/sports/{league_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h"
        
        if options['check_credits']:
            # Use lightweight endpoint
            try:
                resp = requests.get(f"{base_url}/sports/?apiKey={api_key}")
                resp.raise_for_status()
                remaining = int(resp.headers.get('x-requests-remaining', 0))
                used = int(resp.headers.get('x-requests-used', 0))
                self.stdout.write(f"API Credits (Upcoming): Used {used}, Remaining {remaining}")
                return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to check credits: {e}"))
                return

        self.stdout.write(f"Fetching fixtures for {league_key}...")
        
        try:
            response = requests.get(url)
            
            # Check credits from this response
            remaining = int(response.headers.get('x-requests-remaining', 0))
            used = int(response.headers.get('x-requests-used', 0))
            
            # Log to DB
            try:
                APIUsage.objects.update_or_create(
                    api_name="The Odds API (Upcoming - Argentina)",
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
            
            # Identify League in DB
            # Hardcoded mapping for now, can be expanded
            if league_key == 'soccer_argentina_primera_division':
                league_name = 'Liga Profesional'
                country = 'Argentina'
            else:
                self.stdout.write(self.style.WARNING(f"League mapping not defined for {league_key}"))
                return

            league_obj = League.objects.filter(name__icontains=league_name, country__icontains=country).first()
            if not league_obj:
                self.stdout.write(self.style.ERROR(f"League {league_name} ({country}) not found in DB."))
                return

            # Get or Create Season 2026
            current_year = 2026 # Force 2026 for now as we know it's the issue
            season_obj, _ = Season.objects.get_or_create(year=current_year)

            updates = 0
            creates = 0

            for m in matches_data:
                # m keys: id, sport_key, commence_time, home_team, away_team, bookmakers
                commence_time = m['commence_time'] # ISO 8601 string: 2026-02-24T20:00:00Z
                home_team_raw = m['home_team']
                away_team_raw = m['away_team']
                
                # Parse date
                # datetime.strptime handles 'Z' with %z in newer python, but let's be safe
                # replace Z with +00:00 for strict ISO
                commence_time = commence_time.replace('Z', '+00:00')
                dt_obj = datetime.fromisoformat(commence_time)
                
                # Resolve Teams
                home_team = self.resolve_team(home_team_raw, league_obj)
                away_team = self.resolve_team(away_team_raw, league_obj)
                
                if not home_team or not away_team:
                    self.stdout.write(self.style.WARNING(f"Skipping {home_team_raw} vs {away_team_raw} - Team not found"))
                    continue

                # Check if match exists (by teams and approx date)
                # We use a wider window because dates might shift slightly
                start_window = dt_obj - timezone.timedelta(hours=24)
                end_window = dt_obj + timezone.timedelta(hours=24)
                
                match = Match.objects.filter(
                    league=league_obj,
                    home_team=home_team,
                    away_team=away_team,
                    date__range=(start_window, end_window)
                ).first()

                if match:
                    # Update date if changed significantly
                    # Also update status if it was TBD or something
                    time_diff = abs((match.date - dt_obj).total_seconds())
                    if time_diff > 3600: # Changed by more than an hour
                        match.date = dt_obj
                        match.status = 'Scheduled' 
                        match.save()
                        # self.stdout.write(f"Updated time for {home_team} vs {away_team}")
                        updates += 1
                else:
                    # Create new match
                    Match.objects.create(
                        league=league_obj,
                        season=season_obj,
                        home_team=home_team,
                        away_team=away_team,
                        date=dt_obj,
                        status='Scheduled'
                    )
                    self.stdout.write(self.style.SUCCESS(f"Created match: {home_team} vs {away_team} at {dt_obj}"))
                    creates += 1

            self.stdout.write(self.style.SUCCESS(f"Done. Created: {creates}, Updated: {updates}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching odds: {e}"))

    def resolve_team(self, name, league):
        # 1. Exact match
        t = Team.objects.filter(league=league, name__iexact=name).first()
        if t: return t
        
        # 2. Contains match
        t = Team.objects.filter(league=league, name__icontains=name).first()
        if t: return t
        
        # 3. Manual Mappings (Add as needed based on failures)
        mappings = {
            "Central Córdoba (SdE)": "Central Cordoba",
            "Central Córdoba": "Central Cordoba",
            "Argentinos Juniors": "Argentinos Jrs",
            "Atlético Tucumán": "Atl. Tucuman",
            "Defensa y Justicia": "Defensa y Justicia",
            "Deportivo Riestra": "Dep. Riestra",
            "Estudiantes de La Plata": "Estudiantes L.P.",
            "Gimnasia La Plata": "Gimnasia L.P.",
            "Gimnasia y Esgrima (M)": "Gimnasia Mendoza",
            "Gimnasia y Esgrima (Mendoza)": "Gimnasia Mendoza",
            "Godoy Cruz": "Godoy Cruz", # Not in current scraper list but might exist
            "Huracán": "Huracan",
            "Independiente Rivadavia": "Ind. Rivadavia",
            "Instituto (Córdoba)": "Instituto",
            "Instituto de Córdoba": "Instituto",
            "Lanús": "Lanus",
            "Newell's Old Boys": "Newells Old Boys",
            "Newell's": "Newells Old Boys",
            "Sarmiento (Junín)": "Sarmiento Junin",
            "Sarmiento": "Sarmiento Junin",
            "Talleres (Córdoba)": "Talleres Cordoba",
            "Talleres": "Talleres Cordoba",
            "Unión (Santa Fe)": "Union de Santa Fe",
            "Unión": "Union de Santa Fe",
            "Vélez Sarsfield": "Velez Sarsfield",
            "Vélez": "Velez Sarsfield",
            "Barracas Central": "Barracas Central",
            "Banfield": "Banfield",
            "Belgrano": "Belgrano",
            "Boca Juniors": "Boca Juniors",
            "Platense": "Platense",
            "Racing Club": "Racing Club",
            "River Plate": "River Plate",
            "Rosario Central": "Rosario Central",
            "San Lorenzo": "San Lorenzo",
            "Tigre": "Tigre",
            "Estudiantes Río Cuarto": "Estudiantes Rio Cuarto",
            "Estudiantes (RC)": "Estudiantes Rio Cuarto",
            "Aldosivi": "Aldosivi",
            "Independiente": "Independiente",
            "Belgrano de Cordoba": "Belgrano",
            "Atlético Tucuman": "Atl. Tucuman",
            "CA Tigre BA": "Tigre",
            "Velez Sarsfield BA": "Velez Sarsfield",
            "Sarmiento de Junin": "Sarmiento Junin",
            "Union Santa Fe": "Union de Santa Fe",
            "Estudiantes de Río Cuarto": "Estudiantes Rio Cuarto",
            "Atlético Huracán": "Huracan",
            "Aldosivi Mar del Plata": "Aldosivi",
            "Estudiantes": "Estudiantes L.P."
        }
        
        mapped = mappings.get(name)
        if mapped:
            t = Team.objects.filter(league=league, name__iexact=mapped).first()
            if t: return t
            
        return None
