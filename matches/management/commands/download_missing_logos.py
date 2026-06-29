import os
import time
import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings
from matches.models import Team

class Command(BaseCommand):
    help = 'Download missing team logos from Sofascore'

    def handle(self, *args, **options):
        teams = Team.objects.exclude(api_id__isnull=True).exclude(api_id='')
        missing = 0
        downloaded = 0
        failed = 0

        self.stdout.write(f"Total teams to check: {teams.count()}")

        headers = {
            'User-Agent': 'curl/8.4.0'
        }

        for team in teams:
            country_slug = slugify(team.league.country)
            api_id = team.api_id
            
            country_dir = os.path.join(settings.BASE_DIR, 'static', 'teams', country_slug)
            if not os.path.exists(country_dir):
                os.makedirs(country_dir, exist_ok=True)
                
            logo_path = os.path.join(country_dir, f"{api_id}.png")
            
            if not os.path.exists(logo_path):
                missing += 1
                url = f"https://api.sofascore.app/api/v1/team/{api_id}/image"
                
                try:
                    res = requests.get(url, headers=headers, timeout=5)
                    if res.status_code == 200 and len(res.content) > 100:
                        with open(logo_path, 'wb') as f:
                            f.write(res.content)
                        downloaded += 1
                        self.stdout.write(self.style.SUCCESS(f"Downloaded: {team.name} ({country_slug})"))
                    else:
                        failed += 1
                        self.stdout.write(self.style.WARNING(f"Failed to download: {team.name} (Status: {res.status_code})"))
                    
                    time.sleep(0.5) # rate limiting
                except Exception as e:
                    failed += 1
                    self.stdout.write(self.style.ERROR(f"Error downloading {team.name}: {e}"))

        self.stdout.write(f"Done! Missing: {missing}, Downloaded: {downloaded}, Failed: {failed}")
