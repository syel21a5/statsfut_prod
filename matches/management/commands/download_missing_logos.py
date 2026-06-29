import os
import time
import requests
import shutil
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings
from matches.models import Team

class Command(BaseCommand):
    help = 'Download missing team logos directly on the server'

    def handle(self, *args, **options):
        teams = Team.objects.exclude(api_id__isnull=True).exclude(api_id='')
        missing = 0
        downloaded = 0
        failed = 0

        self.stdout.write(f"Total teams to check: {teams.count()}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }

        for team in teams:
            country_slug = slugify(team.league.country)
            api_id = str(team.api_id)
            
            # Paths for source (static) and destination (staticfiles for Nginx)
            static_dir = os.path.join(settings.BASE_DIR, 'static', 'teams', country_slug)
            staticfiles_dir = os.path.join(settings.BASE_DIR, 'staticfiles', 'teams', country_slug)
            
            os.makedirs(static_dir, exist_ok=True)
            os.makedirs(staticfiles_dir, exist_ok=True)
                
            static_path = os.path.join(static_dir, f"{api_id}.png")
            staticfiles_path = os.path.join(staticfiles_dir, f"{api_id}.png")
            
            # If it already exists in staticfiles, we are good.
            if not os.path.exists(staticfiles_path) and not os.path.exists(static_path):
                missing += 1
                
                # Determine URL based on prefix
                if api_id.startswith('sofa_'):
                    real_id = api_id.replace('sofa_', '')
                    url = f"https://api.sofascore.app/api/v1/team/{real_id}/image"
                else:
                    url = f"https://media.api-sports.io/football/teams/{api_id}.png"
                
                try:
                    res = requests.get(url, headers=headers, timeout=10)
                    if res.status_code == 200 and len(res.content) > 100:
                        # Save to both static and staticfiles so it works immediately without collectstatic
                        with open(static_path, 'wb') as f:
                            f.write(res.content)
                        shutil.copy2(static_path, staticfiles_path)
                        
                        downloaded += 1
                        self.stdout.write(self.style.SUCCESS(f"Baixado: {team.name} ({url})"))
                    else:
                        failed += 1
                        self.stdout.write(self.style.WARNING(f"Falha ao baixar: {team.name} (Status: {res.status_code})"))
                    
                    time.sleep(0.3)
                except Exception as e:
                    failed += 1
                    self.stdout.write(self.style.ERROR(f"Erro em {team.name}: {e}"))
            elif os.path.exists(static_path) and not os.path.exists(staticfiles_path):
                # Just copy over
                shutil.copy2(static_path, staticfiles_path)

        self.stdout.write(f"\nFinalizado! Faltavam: {missing}, Baixados: {downloaded}, Falhas: {failed}")
