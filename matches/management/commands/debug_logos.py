import os
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings
from matches.models import Team


class Command(BaseCommand):
    help = 'Debug: mostra quais logos existem e quais estão faltando no servidor'

    def add_arguments(self, parser):
        parser.add_argument('--league', type=str, help='Filtrar por nome da liga (ex: "Serie C")')

    def handle(self, *args, **options):
        league_filter = options.get('league')

        teams = Team.objects.select_related('league').exclude(api_id__isnull=True).exclude(api_id='')
        if league_filter:
            teams = teams.filter(league__name__icontains=league_filter)

        teams = teams.order_by('league__name', 'name')

        static_root = os.path.join(settings.BASE_DIR, 'static')
        staticfiles_root = os.path.join(settings.BASE_DIR, 'staticfiles')

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"DEBUG DE LOGOS - Total de times: {teams.count()}")
        self.stdout.write(f"STATIC dir: {static_root}")
        self.stdout.write(f"STATICFILES dir: {staticfiles_root}")
        self.stdout.write(f"{'='*80}\n")

        current_league = None
        ok_count = 0
        missing_static = 0
        missing_staticfiles = 0
        missing_both = 0
        zero_bytes = 0

        for team in teams:
            if team.league != current_league:
                current_league = team.league
                self.stdout.write(f"\n--- {current_league.name} ({current_league.country}) ---")

            country_slug = slugify(team.league.country)
            api_id = str(team.api_id)
            filename = f"{api_id}.png"

            static_path = os.path.join(static_root, 'teams', country_slug, filename)
            staticfiles_path = os.path.join(staticfiles_root, 'teams', country_slug, filename)

            in_static = os.path.exists(static_path)
            in_staticfiles = os.path.exists(staticfiles_path)

            static_size = os.path.getsize(static_path) if in_static else 0
            staticfiles_size = os.path.getsize(staticfiles_path) if in_staticfiles else 0

            url = f"/static/teams/{country_slug}/{filename}"

            if in_staticfiles and staticfiles_size > 100:
                # OK - exists and has content
                ok_count += 1
            elif in_static and static_size > 100 and not in_staticfiles:
                # Exists in static but not in staticfiles (collectstatic needed)
                missing_staticfiles += 1
                self.stdout.write(self.style.WARNING(
                    f"  FALTA em staticfiles: {team.name} | api_id={api_id} | URL={url} | "
                    f"static={static_size}bytes | staticfiles=MISSING"
                ))
            elif (in_static and static_size == 0) or (in_staticfiles and staticfiles_size == 0):
                zero_bytes += 1
                self.stdout.write(self.style.ERROR(
                    f"  ARQUIVO VAZIO: {team.name} | api_id={api_id} | URL={url} | "
                    f"static={static_size}bytes | staticfiles={staticfiles_size}bytes"
                ))
            else:
                missing_both += 1
                self.stdout.write(self.style.ERROR(
                    f"  SEM ARQUIVO: {team.name} | api_id={api_id} | URL={url}"
                ))

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"RESUMO:")
        self.stdout.write(self.style.SUCCESS(f"  OK (imagem funcionando): {ok_count}"))
        self.stdout.write(self.style.WARNING(f"  Falta em staticfiles (precisa collectstatic): {missing_staticfiles}"))
        self.stdout.write(self.style.ERROR(f"  Arquivo vazio (0 bytes): {zero_bytes}"))
        self.stdout.write(self.style.ERROR(f"  Sem arquivo nenhum: {missing_both}"))
        self.stdout.write(f"{'='*80}\n")
