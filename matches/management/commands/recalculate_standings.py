from django.core.management.base import BaseCommand
from django.db.models import Q

from matches.models import League, Season, Team, Match, LeagueStanding


class Command(BaseCommand):
    help = "Recalcula a tabela de classificação a partir dos jogos do banco"

    def add_arguments(self, parser):
        parser.add_argument(
            "--league_name",
            type=str,
            default="Premier League",
            help="Nome da liga para recalcular a tabela",
        )
        parser.add_argument(
            "--country",
            type=str,
            default=None,
            help="País da liga (opcional, para desambiguação)",
        )
        parser.add_argument(
            "--season_year",
            type=int,
            help="Ano de término da temporada (ex: 2026 para 2025/2026). Se omitido, usa a temporada mais recente com jogos",
        )

    def handle(self, *args, **options):
        league_name = options["league_name"]
        country = options["country"]
        season_year = options.get("season_year")

        try:
            if country:
                # Se passou país, tenta filtrar por ele
                leagues = League.objects.filter(name=league_name, country=country)
            else:
                # Se não passou, busca pelo nome
                leagues = League.objects.filter(name=league_name)

            if not leagues.exists():
                # Fallback: Se for Premier League, tenta filtrar por Inglaterra
                if league_name == "Premier League":
                     leagues = League.objects.filter(name=league_name, country="Inglaterra")
                
                if not leagues.exists():
                    self.stdout.write(self.style.ERROR(f"Liga '{league_name}' (País: {country}) não encontrada"))
                    return

            # Se houver mais de uma liga com o mesmo nome (duplicata suja),
            # pegamos a primeira que tiver jogos, ou simplesmente a primeira (ID menor)
            # O ideal é rodar merge_duplicate_leagues, mas aqui evitamos o crash.
            if leagues.count() > 1:
                self.stdout.write(self.style.WARNING(f"Encontradas {leagues.count()} ligas com nome '{league_name}'. Usando a primeira."))
            
            league = leagues.first()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao buscar liga: {e}"))
            return

        if season_year:
            season = Season.objects.filter(year=season_year).first()
            if not season:
                self.stdout.write(self.style.ERROR(f"Temporada {season_year} não encontrada"))
                return
        else:
            season = (
                Season.objects.filter(matches__league=league)
                .distinct()
                .order_by("-year")
                .first()
            )
            if not season:
                self.stdout.write(self.style.ERROR("Nenhuma temporada com jogos encontrada para esta liga"))
                return

        self.stdout.write(
            self.style.SUCCESS(
                f"Recalculando tabela para {league.name}, temporada {season.year}"
            )
        )

        finished_matches = Match.objects.filter(
            league=league,
            season=season,
            status="Finished",
            home_score__isnull=False,
            away_score__isnull=False,
        ).select_related("home_team", "away_team")

        if not finished_matches.exists():
            self.stdout.write(self.style.WARNING("Nenhum jogo finalizado encontrado para esta liga/temporada"))
            return

        if league.country == "Alemanha":
            base_qs = finished_matches
        else:
            base_qs = Match.objects.filter(league=league, season=season)

        # Pegamos os IDs usando a base_qs (jogos Finished ou Scheduled desta season)
        # Isso garante que pegamos APENAS times que vão jogar/já jogaram nessa temporada,
        # NUNCA puxar todos os times da liga (para evitar times de temporadas antigas ou duplicatas que não foram totalmente expurgadas).
        season_team_ids = set(
            base_qs.values_list("home_team_id", flat=True)
        ) | set(
            base_qs.values_list("away_team_id", flat=True)
        )

        if not season_team_ids:
            self.stdout.write(self.style.WARNING("Nenhum jogo (nem agendado) encontrado para definir os times da temporada. Tabela não será gerada."))
            return
            
        # Pega os objetos dos times
        teams = Team.objects.filter(id__in=season_team_ids)

        stats_by_team = {}
        for team in teams:
            stats_by_team[team.id] = {
                "team": team,
                "played": 0,
                "won": 0,
                "drawn": 0,
                "lost": 0,
                "gf": 0,
                "ga": 0,
                "points": 0,
            }

        for m in finished_matches:
            home_id = m.home_team_id
            away_id = m.away_team_id

            if home_id not in stats_by_team or away_id not in stats_by_team:
                continue

            home_stats = stats_by_team[home_id]
            away_stats = stats_by_team[away_id]

            home_stats["played"] += 1
            away_stats["played"] += 1

            home_goals = m.home_score or 0
            away_goals = m.away_score or 0

            home_stats["gf"] += home_goals
            home_stats["ga"] += away_goals
            away_stats["gf"] += away_goals
            away_stats["ga"] += home_goals

            if home_goals > away_goals:
                home_stats["won"] += 1
                home_stats["points"] += 3
                away_stats["lost"] += 1
            elif home_goals < away_goals:
                away_stats["won"] += 1
                away_stats["points"] += 3
                home_stats["lost"] += 1
            else:
                home_stats["drawn"] += 1
                away_stats["drawn"] += 1
                home_stats["points"] += 1
                away_stats["points"] += 1

        teams_stats = [
            (
                data["team"],
                data["played"],
                data["won"],
                data["drawn"],
                data["lost"],
                data["gf"],
                data["ga"],
                data["points"],
            )
            for data in stats_by_team.values()
        ]

        teams_stats.sort(
            key=lambda item: (
                -item[7],
                - (item[5] - item[6]),
                -item[5],
                item[0].name,
            )
        )

        LeagueStanding.objects.filter(league=league, season=season).delete()

        created = 0
        for idx, (team, played, won, drawn, lost, gf, ga, pts) in enumerate(teams_stats, start=1):
            LeagueStanding.objects.create(
                league=league,
                season=season,
                team=team,
                position=idx,
                played=played,
                won=won,
                drawn=drawn,
                lost=lost,
                goals_for=gf,
                goals_against=ga,
                points=pts,
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Tabela recalculada. Times atualizados: {created}"
            )
        )
