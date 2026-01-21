from django.core.management.base import BaseCommand
from django.db.models import Q

from matches.models import League, Season, Match
from matches.api_manager import APIManager


class Command(BaseCommand):
    help = "Compara resultados da Premier League na temporada atual com a API de temporada (Football-Data.org) e lista divergências"

    def add_arguments(self, parser):
        parser.add_argument(
            "--league_id",
            type=int,
            default=2021,
            help="ID da competição na Football-Data.org (padrão: 2021 = Premier League)",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Se informado, atualiza os placares do banco para bater com a API",
        )

    def handle(self, *args, **options):
        league_id = options["league_id"]
        fix = options["fix"]

        try:
            league = League.objects.get(name="Premier League")
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR("Liga 'Premier League' não encontrada no banco."))
            return

        try:
            season = Season.objects.latest("year")
        except Season.DoesNotExist:
            self.stdout.write(self.style.ERROR("Nenhuma temporada cadastrada."))
            return

        api_manager = APIManager()

        self.stdout.write(
            self.style.SUCCESS(
                f"Buscando fixtures da API-Football para league={league_id}, season={season.year}..."
            )
        )

        try:
            fixtures = api_manager.get_league_season_fixtures(league_id=league_id, season_year=season.year)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao buscar fixtures na API-Football: {e}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Total de fixtures retornadas pela API: {len(fixtures)}"))

        def norm_name(name: str) -> str:
            return (
                name.replace(" FC", "")
                .replace("AFC ", "")
                .strip()
                .lower()
            )

        fixtures_map = {}
        for f in fixtures:
            if f["date"] is None:
                continue
            try:
                date_str = f["date"][:10]
            except Exception:
                continue
            key = (
                date_str,
                norm_name(f["home_team"]),
                norm_name(f["away_team"]),
            )
            fixtures_map[key] = (f["home_score"], f["away_score"])

        db_matches = Match.objects.filter(
            league=league,
            season=season,
            status="Finished",
            home_score__isnull=False,
            away_score__isnull=False,
        )

        diffs = []
        total_checked = 0

        for m in db_matches:
            if not m.date:
                continue
            date_str = m.date.date().isoformat()
            key = (
                date_str,
                norm_name(m.home_team.name),
                norm_name(m.away_team.name),
            )

            api_scores = fixtures_map.get(key)
            if api_scores is None:
                continue

            total_checked += 1
            api_home, api_away = api_scores

            if api_home is None or api_away is None:
                continue

            if m.home_score != api_home or m.away_score != api_away:
                diffs.append((m, api_home, api_away))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Jogos conferidos com a API-Football: {total_checked}"))

        if not diffs:
            self.stdout.write(self.style.SUCCESS("Nenhuma divergência de placar encontrada."))
            return

        self.stdout.write(self.style.WARNING(f"Foram encontradas {len(diffs)} divergências:"))

        for m, api_home, api_away in diffs:
            self.stdout.write(
                f"- {m.date.date()} | {m.home_team.name} x {m.away_team.name} | "
                f"banco: {m.home_score}-{m.away_score} | api: {api_home}-{api_away}"
            )

        if not fix:
            self.stdout.write(
                self.style.WARNING(
                    "Use --fix para atualizar automaticamente os placares divergentes com os valores da API."
                )
            )
            return

        updated = 0
        for m, api_home, api_away in diffs:
            m.home_score = api_home
            m.away_score = api_away
            m.status = "Finished"
            m.save(update_fields=["home_score", "away_score", "status"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Atualização concluída. Jogos atualizados: {updated}")
        )
