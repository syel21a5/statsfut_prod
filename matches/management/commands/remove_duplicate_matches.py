from django.core.management.base import BaseCommand
from matches.models import League, Match
from django.db.models import Q
from django.utils import timezone



FINISHED_STATUSES = ['Finished', 'FT', 'AET', 'PEN', 'FINISHED']


class Command(BaseCommand):
    help = "Remove partidas duplicadas de uma liga. Detecta duplicatas pelo mesmo par de times no mesmo dia do calendário."

    def add_arguments(self, parser):
        parser.add_argument(
            '--league_name', type=str, default=None,
            help='Nome da liga para filtrar (ex: "Brasileirao"). Se omitido, verifica TODAS as ligas.'
        )
        parser.add_argument(
            '--country', type=str, default=None,
            help='País da liga para filtrar (ex: "Brasil").'
        )
        parser.add_argument(
            '--dry_run', action='store_true', default=False,
            help='Apenas exibe os duplicados sem deletar nada.'
        )

    def handle(self, *args, **options):
        league_name = options.get('league_name')
        country = options.get('country')
        dry_run = options.get('dry_run')

        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  MODO DRY RUN: Nenhum registro será deletado."))

        # Seleciona as ligas
        if league_name:
            qs = League.objects.all()
            if country:
                qs = qs.filter(name__iexact=league_name, country__iexact=country)
            else:
                qs = qs.filter(name__iexact=league_name)
            leagues = list(qs)
        else:
            leagues = list(League.objects.all())

        if not leagues:
            self.stdout.write(self.style.ERROR("Nenhuma liga encontrada com os filtros fornecidos."))
            return

        total_deleted = 0

        for league in leagues:
            self.stdout.write(f"\n📋 Verificando: {league.name} ({league.country}) - ID: {league.id}")

            matches = Match.objects.filter(league=league).select_related(
                'home_team', 'away_team', 'season'
            ).order_by('date', 'id')

            # Agrupa por (data_calendario, home_team_id, away_team_id)
            seen = {}
            for match in matches:
                if not match.date:
                    continue
                # Usa apenas a data do calendário local, ignora horário
                day_key = timezone.localtime(match.date).date()
                key = (day_key, match.home_team_id, match.away_team_id)

                if key not in seen:
                    seen[key] = []
                seen[key].append(match)

            league_deleted = 0
            for key, match_list in seen.items():
                if len(match_list) <= 1:
                    continue

                home_name = match_list[0].home_team.name
                away_name = match_list[0].away_team.name
                date_str = key[0].strftime('%d/%m/%Y')

                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠️  Duplicata ({len(match_list)}x): {home_name} vs {away_name} em {date_str}"
                    )
                )

                # Estratégia de escolha do "keeper":
                # 1. Prefere o que tem api_id do SofaScore (sofa_XXXX)
                # 2. Depois, o que tem status "FT" / "Finished"
                # 3. Por último, o de ID menor (mais antigo)
                def sort_key(m):
                    has_sofa_id = 1 if (m.api_id and m.api_id.startswith('sofa_')) else 0
                    is_finished = 1 if m.status in FINISHED_STATUSES else 0
                    has_score = 1 if (m.home_score is not None and m.away_score is not None) else 0
                    return (-has_sofa_id, -is_finished, -has_score, m.id)

                match_list.sort(key=sort_key)
                keeper = match_list[0]
                to_delete = match_list[1:]

                self.stdout.write(
                    f"    ✅ Mantendo ID: {keeper.id} | api_id: {keeper.api_id} | "
                    f"status: {keeper.status} | placar: {keeper.home_score}-{keeper.away_score}"
                )

                for d in to_delete:
                    self.stdout.write(
                        f"    🗑️  Deletando ID: {d.id} | api_id: {d.api_id} | "
                        f"status: {d.status} | placar: {d.home_score}-{d.away_score}"
                    )
                    if not dry_run:
                        d.delete()
                        league_deleted += 1

            if league_deleted > 0:
                self.stdout.write(self.style.SUCCESS(f"  → {league_deleted} duplicata(s) removida(s) de {league.name}."))
            else:
                self.stdout.write(f"  → Nenhuma duplicata encontrada em {league.name}.")

            total_deleted += league_deleted

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Concluído! Total de duplicatas removidas: {total_deleted}")
        )
