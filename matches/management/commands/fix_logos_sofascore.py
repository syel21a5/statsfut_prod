import os
import requests
import time
import shutil
import urllib.parse
from django.core.management.base import BaseCommand
from matches.models import Team
from django.conf import settings
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Baixa logos faltantes buscando no Sofascore'

    def handle(self, *args, **options):
        teams = Team.objects.all().order_by('league__country', 'name')
        
        static_root = os.path.join(settings.BASE_DIR, 'static')
        staticfiles_root = os.path.join(settings.BASE_DIR, 'staticfiles')
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Referer': 'https://www.sofascore.com/'
        }

        downloaded = 0
        failed = 0
        already_ok = 0

        self.stdout.write(self.style.SUCCESS("Iniciando busca inteligente no Sofascore..."))

        for team in teams:
            if not team.api_id or not team.league or not team.league.country:
                continue

            country_slug = slugify(team.league.country)
            filename = f"{team.api_id}.png"
            
            static_dir = os.path.join(static_root, 'teams', country_slug)
            staticfiles_dir = os.path.join(staticfiles_root, 'teams', country_slug)
            static_path = os.path.join(static_dir, filename)
            staticfiles_path = os.path.join(staticfiles_dir, filename)

            if os.path.exists(static_path):
                size = os.path.getsize(static_path)
                if size > 100 and size != 90381:
                    already_ok += 1
                    continue

            # Busca no TheSportsDB
            query = urllib.parse.quote(team.name)
            search_url = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={query}"
            
            badge_url = None
            try:
                resp = requests.get(search_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    teams_data = data.get('teams')
                    if teams_data:
                        # Pega o primeiro time retornado
                        badge_url = teams_data[0].get('strBadge')
            except Exception as e:
                pass
                
            if not badge_url:
                failed += 1
                self.stdout.write(self.style.WARNING(f"  ⚠️ {team.name} -> Não achou no TheSportsDB"))
                time.sleep(0.5)
                continue
            
            try:
                resp = requests.get(badge_url, headers=headers, timeout=10)
                if resp.status_code == 200 and len(resp.content) > 100:
                    os.makedirs(static_dir, exist_ok=True)
                    os.makedirs(staticfiles_dir, exist_ok=True)
                    
                    with open(static_path, 'wb') as f:
                        f.write(resp.content)
                    shutil.copy2(static_path, staticfiles_path)
                    
                    downloaded += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✅ {team.name} -> Achou no TheSportsDB!"))
                else:
                    failed += 1
                    self.stdout.write(self.style.ERROR(f"  ❌ {team.name} -> Logo indisponível no TheSportsDB"))
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  ❌ Erro ao baixar {team.name} do TheSportsDB"))
                
            time.sleep(0.5) # Limite educado

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"  Já estavam OK: {already_ok}"))
        self.stdout.write(self.style.SUCCESS(f"  Salvos do Sofascore Search: {downloaded}"))
        self.stdout.write(self.style.ERROR(f"  Falhas: {failed}"))
        self.stdout.write(f"{'='*60}\n")
