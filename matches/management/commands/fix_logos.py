import os
import time
import shutil
import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings
from matches.models import Team
from matches.api_manager import APIManager


class Command(BaseCommand):
    help = 'Baixa TODAS as logos faltantes verificando pelo nome na API (cara-crachá)'

    def add_arguments(self, parser):
        parser.add_argument('--league', type=str, help='Filtrar por nome da liga')
        parser.add_argument('--country', type=str, help='Filtrar por pais')

    def handle(self, *args, **options):
        league_filter = options.get('league')
        country_filter = options.get('country')

        teams = Team.objects.select_related('league').exclude(api_id__isnull=True).exclude(api_id='')

        if league_filter:
            teams = teams.filter(league__name__icontains=league_filter)
        if country_filter:
            teams = teams.filter(league__country__icontains=country_filter)

        static_root = os.path.join(settings.BASE_DIR, 'static')
        staticfiles_root = os.path.join(settings.BASE_DIR, 'staticfiles')

        # Separar times que já têm logo dos que não têm
        missing_teams = []
        already_ok = 0

        for team in teams:
            country_slug = slugify(team.league.country)
            api_id = str(team.api_id)
            filename = f"{api_id}.png"

            staticfiles_dir = os.path.join(staticfiles_root, 'teams', country_slug)
            staticfiles_path = os.path.join(staticfiles_dir, filename)

            static_dir = os.path.join(static_root, 'teams', country_slug)
            static_path = os.path.join(static_dir, filename)

            has_staticfiles = os.path.exists(staticfiles_path) and os.path.getsize(staticfiles_path) > 100
            has_static = os.path.exists(static_path) and os.path.getsize(static_path) > 100

            # FORCE redownload se for um ID inválido que pode ter baixado logo errada na versão anterior
            if api_id.startswith('ignored_') or api_id.startswith('sofa_'):
                has_staticfiles = False
                has_static = False

            if has_staticfiles:
                already_ok += 1
            elif has_static:
                # Só precisa copiar
                os.makedirs(staticfiles_dir, exist_ok=True)
                shutil.copy2(static_path, staticfiles_path)
                already_ok += 1
                self.stdout.write(self.style.SUCCESS(f"  COPIADO: {team.name}"))
            else:
                missing_teams.append(team)

        self.stdout.write(f"\nJá OK: {already_ok}")
        self.stdout.write(f"Faltam baixar: {len(missing_teams)}")

        if not missing_teams:
            self.stdout.write(self.style.SUCCESS("\nTodos os times já têm logo!"))
            return

        # Inicializar API Manager para buscar times pelo nome
        api_mgr = APIManager()
        api_config = api_mgr.apis.get('api_football_1')
        if not api_config or not api_config.get('key'):
            self.stdout.write(self.style.ERROR("API_FOOTBALL_KEY não configurada!"))
            return

        headers_api = api_mgr._get_headers(api_config)
        headers_download = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        downloaded = 0
        failed = 0

        for team in missing_teams:
            country_slug = slugify(team.league.country)
            api_id = str(team.api_id)
            filename = f"{api_id}.png"
            static_dir = os.path.join(static_root, 'teams', country_slug)
            staticfiles_dir = os.path.join(staticfiles_root, 'teams', country_slug)
            static_path = os.path.join(static_dir, filename)
            staticfiles_path = os.path.join(staticfiles_dir, filename)

            # CARA-CRACHÁ: Buscar o time pelo nome na API-Football
            search_name = team.name
            try:
                search_url = f"{api_config['base_url']}/teams"
                params = {'search': search_name}
                resp = requests.get(search_url, headers=headers_api, params=params, timeout=10)

                if resp.status_code != 200:
                    self.stdout.write(self.style.ERROR(
                        f"  ERRO API: {team.name} | Status {resp.status_code}"))
                    failed += 1
                    time.sleep(1)
                    continue

                data = resp.json()
                results = data.get('response', [])

                if not results:
                    # Tentar com nome mais curto (primeira palavra)
                    short_name = search_name.split()[0] if ' ' in search_name else search_name
                    params = {'search': short_name}
                    resp = requests.get(search_url, headers=headers_api, params=params, timeout=10)
                    if resp.status_code == 200:
                        results = resp.json().get('response', [])

                if results:
                    # Pega o primeiro resultado (mais relevante)
                    found_team = results[0]['team']
                    found_id = found_team['id']
                    found_name = found_team['name']
                    logo_url = found_team.get('logo', '')

                    if logo_url:
                        # Baixar a logo oficial
                        img_resp = requests.get(logo_url, headers=headers_download, timeout=10)
                        if img_resp.status_code == 200 and len(img_resp.content) > 100:
                            os.makedirs(static_dir, exist_ok=True)
                            os.makedirs(staticfiles_dir, exist_ok=True)
                            with open(static_path, 'wb') as f:
                                f.write(img_resp.content)
                            shutil.copy2(static_path, staticfiles_path)
                            downloaded += 1
                            self.stdout.write(self.style.SUCCESS(
                                f"  ✅ {team.name} → API encontrou: {found_name} (ID:{found_id})"))
                        else:
                            failed += 1
                            self.stdout.write(self.style.ERROR(
                                f"  ❌ {team.name} → Logo URL falhou: {logo_url}"))
                    else:
                        failed += 1
                        self.stdout.write(self.style.ERROR(
                            f"  ❌ {team.name} → Sem logo URL no resultado"))
                else:
                    failed += 1
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠️ {team.name} → Não encontrado na API"))

                time.sleep(0.5)  # Rate limit

            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  ERRO: {team.name} | {e}"))

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"  Já OK: {already_ok}"))
        self.stdout.write(self.style.SUCCESS(f"  Baixados (cara-crachá): {downloaded}"))
        self.stdout.write(self.style.ERROR(f"  Falhas: {failed}"))
        self.stdout.write(f"{'='*60}\n")
