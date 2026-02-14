
import os
import time
import pandas as pd
import random
from io import StringIO
from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season
from django.utils import timezone
from datetime import datetime
import pytz
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Command(BaseCommand):
    help = 'Scrape historical data directly from FBref using Selenium and pandas'

    def add_arguments(self, parser):
        parser.add_argument('--seasons', nargs='+', type=str, help='Seasons to scrape (e.g., 2023 2024)')
        parser.add_argument('--league', type=str, help='League to scrape (PL or BR)')
        parser.add_argument('--csv_only', action='store_true', help='Save to CSV only, do not import to DB')

    def handle(self, *args, **kwargs):
        # Configuration
        csv_only = kwargs['csv_only']
        if csv_only:
             # Default to full history for CSV export if not specified
             target_seasons = kwargs['seasons'] or [str(y) for y in range(2010, 2026)]
        else:
             target_seasons = kwargs['seasons'] or ['2020', '2021', '2022', '2023', '2024', '2025']
        
        target_league_code = kwargs['league'] 
        
        # Ensure export directory exists
        base_dir = "csv_exports"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        leagues_config = {
            'PL': {
                'id': '9',
                'name': 'Premier League',
                'country': 'Inglaterra',
                'slug': 'Premier-League',
                'season_format': 'spanning' 
            },
            'BR': {
                'id': '24',
                'name': 'Brasileirão',
                'country': 'Brasil',
                'slug': 'Serie-A',
                'season_format': 'single'
            }
        }

        leagues_to_process = leagues_config.items()
        if target_league_code:
            if target_league_code in leagues_config:
                leagues_to_process = [(target_league_code, leagues_config[target_league_code])]
            else:
                self.stdout.write(self.style.ERROR(f"Invalid league code. Use PL or BR."))
                return
        
        # Initialize Browser
        options = uc.ChromeOptions()
        options.add_argument('--headless=new') 
        options.add_argument('--no-sandbox')
        
        try:
            with open('scrape_debug.txt', 'w') as log_file:
                log_file.write("Starting browser...\n")
                driver = uc.Chrome(options=options)
                log_file.write("Browser started.\n")

                for code, config in leagues_to_process:
                    log_file.write(f"--- Processing {config['name']} ---\n")
                    self.stdout.write(self.style.SUCCESS(f"--- Processing {config['name']} ---"))
                    
                    league_obj = None
                    if not csv_only:
                        league_obj, _ = League.objects.get_or_create(
                            name=config['name'], 
                            country=config['country']
                        )

                    for year in target_seasons:
                        url = self.build_url(config, year)
                        if not url:
                            continue

                        log_file.write(f"Scraping {year}: {url}\n")
                        self.stdout.write(f"Scraping {year}: {url}")
                        
                        try:
                            driver.get(url)
                            
                            # Wait for table
                            try:
                                WebDriverWait(driver, 15).until(
                                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                                )
                            except:
                                log_file.write("Timeout waiting for table\n")
                                self.stdout.write(self.style.WARNING("Timeout waiting for table"))

                            html = driver.page_source
                            
                            # Check for 429/403 text
                            if "429 Too Many Requests" in html:
                                log_file.write("Rate limit hit (429). Sleeping 60s...\n")
                                self.stdout.write(self.style.ERROR("Rate limit hit (429). Sleeping 60s..."))
                                time.sleep(60)
                                driver.get(url) # Retry once
                                html = driver.page_source

                            dfs = pd.read_html(StringIO(html))
                            
                            found_df = None
                            for df in dfs:
                                cols = [str(c).lower() for c in df.columns]
                                if any('data' in c for c in cols) and any('placar' in c or 'score' in c for c in cols):
                                    found_df = df
                                    break
                            
                            if found_df is None and dfs:
                                 found_df = max(dfs, key=len)

                            if found_df is not None:
                                # Save CSV
                                filename = f"{base_dir}/{config['slug'].lower()}_fbref_{year}.csv"
                                found_df.to_csv(filename, index=False, encoding='utf-8')
                                log_file.write(f"Saved CSV: {filename}\n")
                                self.stdout.write(self.style.SUCCESS(f"Saved CSV: {filename}"))

                                if not csv_only:
                                    self.save_match_data(found_df, league_obj, year)
                            else:
                                log_file.write("No suitable table found.\n")
                                self.stdout.write(self.style.WARNING("No suitable table found."))

                            # Rate limiting
                            sleep_time = random.uniform(5, 8)
                            self.stdout.write(f"Sleeping {sleep_time:.1f}s...")
                            time.sleep(sleep_time)

                        except Exception as e:
                            log_file.write(f"Error processing {year}: {e}\n")
                            self.stdout.write(self.style.ERROR(f"Error processing {year}: {e}"))
        
        except Exception as e:
            with open('scrape_error.txt', 'w') as f:
                f.write(str(e))
            raise e
        finally:
            if 'driver' in locals():
                driver.quit()

    def build_url(self, config, year_str):
        base = "https://fbref.com/pt/comps"
        comp_id = config['id']
        slug = config['slug']
        
        try:
            y = int(year_str)
        except:
            return None

        if config['season_format'] == 'spanning':
            season_param = f"{y}-{y+1}"
        else:
            season_param = f"{y}"

        return f"{base}/{comp_id}/{season_param}/cronograma/{season_param}-{slug}-Resultados-e-Calendarios"

    def save_match_data(self, df, league_obj, year_str):
        df.columns = [c.lower() for c in df.columns]
        count_new = 0
        count_updated = 0
        
        try:
            season_year = int(year_str)
            if league_obj.name == 'Premier League':
                season_obj, _ = Season.objects.get_or_create(year=season_year + 1)
            else:
                season_obj, _ = Season.objects.get_or_create(year=season_year)
        except:
            season_obj = None

        for idx, row in df.iterrows():
            try:
                if 'mandante' not in row or 'visitante' not in row:
                    continue
                
                home_name = row['mandante']
                away_name = row['visitante']
                
                if home_name == 'Mandante' or pd.isna(home_name):
                    continue
                
                home_team, _ = Team.objects.get_or_create(name=home_name, league=league_obj)
                away_team, _ = Team.objects.get_or_create(name=away_name, league=league_obj)
                
                date_str = row.get('data', None)
                time_str = row.get('hora', '')
                
                match_dt = None
                if date_str and isinstance(date_str, str):
                    try:
                        dt_str = date_str
                        if time_str and isinstance(time_str, str):
                            dt_str += f" {time_str}"
                            fmt = "%Y-%m-%d %H:%M"
                        else:
                            fmt = "%Y-%m-%d"
                        
                        match_dt = datetime.strptime(dt_str, fmt)
                        match_dt = timezone.make_aware(match_dt, pytz.UTC)
                    except:
                        pass
                
                score_raw = row.get('placar', None)
                home_score = None
                away_score = None
                status = 'Scheduled'
                
                if score_raw and isinstance(score_raw, str):
                    if '–' in score_raw: 
                        parts = score_raw.split('–')
                        home_score = int(parts[0])
                        away_score = int(parts[1])
                        status = 'Finished'
                    elif '-' in score_raw:
                        parts = score_raw.split('-')
                        home_score = int(parts[0])
                        away_score = int(parts[1])
                        status = 'Finished'
                
                defaults = {
                    'home_score': home_score,
                    'away_score': away_score,
                    'status': status,
                    'date': match_dt
                }
                
                match_obj, created = Match.objects.update_or_create(
                    league=league_obj,
                    season=season_obj,
                    home_team=home_team,
                    away_team=away_team,
                    defaults=defaults
                )

                if created:
                    count_new += 1
                else:
                    count_updated += 1
            except:
                continue
                
        self.stdout.write(self.style.SUCCESS(f"  Saved: {count_new} new, {count_updated} updated"))
