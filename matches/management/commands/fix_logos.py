import os
import time
import shutil
import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings
from matches.models import Team


class Command(BaseCommand):
    help = 'Baixa TODAS as logos faltantes (inclusive ignored_) e copia para staticfiles'

    def add_arguments(self, parser):
        parser.add_argument('--league', type=str, help='Filtrar por nome da liga')
        parser.add_argument('--country', type=str, help='Filtrar por pais')
        parser.add_argument('--dry-run', action='store_true', help='Apenas mostra o que faria')

    def handle(self, *args, **options):
        league_filter = options.get('league')
        country_filter = options.get('country')
        dry_run = options.get('dry_run', False)

        teams = Team.objects.select_related('league').exclude(api_id__isnull=True).exclude(api_id='')

        if league_filter:
            teams = teams.filter(league__name__icontains=league_filter)
        if country_filter:
            teams = teams.filter(league__country__icontains=country_filter)

        static_root = os.path.join(settings.BASE_DIR, 'static')
        staticfiles_root = os.path.join(settings.BASE_DIR, 'staticfiles')

        self.stdout.write(f"\nTotal times a verificar: {teams.count()}")
        if dry_run:
            self.stdout.write(self.style.WARNING("MODO DRY-RUN: nenhum arquivo será baixado"))

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        downloaded = 0
        copied = 0
        already_ok = 0
        failed = 0

        for team in teams:
            country_slug = slugify(team.league.country)
            api_id = str(team.api_id)
            filename = f"{api_id}.png"

            static_dir = os.path.join(static_root, 'teams', country_slug)
            staticfiles_dir = os.path.join(staticfiles_root, 'teams', country_slug)
            static_path = os.path.join(static_dir, filename)
            staticfiles_path = os.path.join(staticfiles_dir, filename)

            # Verificar se o arquivo existe e tem conteúdo válido
            has_static = os.path.exists(static_path) and os.path.getsize(static_path) > 100
            has_staticfiles = os.path.exists(staticfiles_path) and os.path.getsize(staticfiles_path) > 100

            if has_staticfiles:
                already_ok += 1
                continue

            if has_static and not has_staticfiles:
                if not dry_run:
                    os.makedirs(staticfiles_dir, exist_ok=True)
                    shutil.copy2(static_path, staticfiles_path)
                copied += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  COPIADO: {team.name} ({team.league.name}) → staticfiles"))
                continue

            # Determinar o ID real para download
            # ignored_4503 → 4503 (ID numérico válido na API-Football)
            # sofa_1997 → 1997 (ID do Sofascore)
            # 144 → 144 (ID numérico da API-Football)
            if api_id.startswith('ignored_'):
                real_id = api_id.replace('ignored_', '')
                # Tenta API-Football primeiro com o número real
                url = f"https://media.api-sports.io/football/teams/{real_id}.png"
            elif api_id.startswith('sofa_'):
                real_id = api_id.replace('sofa_', '')
                url = f"https://api.sofascore.app/api/v1/team/{real_id}/image"
            else:
                url = f"https://media.api-sports.io/football/teams/{api_id}.png"

            if dry_run:
                self.stdout.write(self.style.WARNING(
                    f"  FALTA: {team.name} ({team.league.name}) | {api_id} → {url}"))
                failed += 1
                continue

            try:
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200 and len(res.content) > 100:
                    os.makedirs(static_dir, exist_ok=True)
                    os.makedirs(staticfiles_dir, exist_ok=True)
                    # Salva com o nome do api_id original (incluindo ignored_ ou sofa_)
                    with open(static_path, 'wb') as f:
                        f.write(res.content)
                    shutil.copy2(static_path, staticfiles_path)
                    downloaded += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  BAIXADO: {team.name} ({team.league.name}) ← {url}"))
                else:
                    # Se falhou com Sofascore, tenta API-Football como fallback
                    if api_id.startswith('sofa_'):
                        fallback_url = f"https://media.api-sports.io/football/teams/{real_id}.png"
                        res2 = requests.get(fallback_url, headers=headers, timeout=10)
                        if res2.status_code == 200 and len(res2.content) > 100:
                            os.makedirs(static_dir, exist_ok=True)
                            os.makedirs(staticfiles_dir, exist_ok=True)
                            with open(static_path, 'wb') as f:
                                f.write(res2.content)
                            shutil.copy2(static_path, staticfiles_path)
                            downloaded += 1
                            self.stdout.write(self.style.SUCCESS(
                                f"  BAIXADO (fallback): {team.name} ({team.league.name}) ← {fallback_url}"))
                        else:
                            failed += 1
                            self.stdout.write(self.style.ERROR(
                                f"  FALHA: {team.name} ({team.league.name}) | {api_id} | Status {res.status_code}/{res2.status_code}"))
                    else:
                        failed += 1
                        self.stdout.write(self.style.ERROR(
                            f"  FALHA: {team.name} ({team.league.name}) | {api_id} | Status {res.status_code} | {url}"))
                time.sleep(0.3)
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(
                    f"  ERRO: {team.name} ({team.league.name}) | {e}"))

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"  Já OK: {already_ok}"))
        self.stdout.write(self.style.SUCCESS(f"  Copiados (static→staticfiles): {copied}"))
        self.stdout.write(self.style.SUCCESS(f"  Baixados da internet: {downloaded}"))
        self.stdout.write(self.style.ERROR(f"  Falhas: {failed}"))
        self.stdout.write(f"{'='*60}\n")
