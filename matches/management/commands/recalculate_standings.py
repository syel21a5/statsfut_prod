from django.core.management.base import BaseCommand
from django.db.models import Q

from matches.models import League, Season, Team, Match, LeagueStanding


class Command(BaseCommand):
    help = "Recalcula a tabela de classificação a partir dos jogos do banco"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Recalcula a tabela para todas as ligas ativas",
        )
        parser.add_argument(
            "--league_name",
            type=str,
            default=None,
            help="Nome da liga para recalcular a tabela",
        )
        parser.add_argument(
            "--country",
            type=str,
            default=None,
            help="País da liga (opcional, para desambiguação)",
        )
        parser.add_argument(
            "--division",
            type=str,
            help="Código da divisão (ex: AUT, E0) para configurar liga/país automaticamente",
        )
        parser.add_argument(
            "--season_year",
            type=int,
            help="Ano de término da temporada (ex: 2026 para 2025/2026). Se omitido, usa a temporada mais recente com jogos",
        )

    def handle(self, *args, **options):
        if options["all"]:
            leagues_with_matches = League.objects.filter(matches__isnull=False).distinct()
            self.stdout.write(self.style.SUCCESS(f"Iniciando recálculo para {leagues_with_matches.count()} ligas ativas..."))
            for league in leagues_with_matches:
                self.recalculate_for_league(league)
            self.stdout.write(self.style.SUCCESS("Recálculo de todas as ligas concluído."))
            return

        league_name = options["league_name"]
        country = options["country"]
        division = options.get("division")
        season_year = options.get("season_year")

        if not league_name and not division:
            self.stdout.write(self.style.ERROR("Você precisa especificar --league_name, --division ou usar --all."))
            return
        
        # Mapeamento auxiliar se usar --division
        LEAGUE_MAPPING = {
            'E0': ('Premier League', 'Inglaterra'),
            'SP1': ('La Liga', 'Espanha'),
            'D1': ('Bundesliga', 'Alemanha'),
            'I1': ('Serie A', 'Italia'),
            'F1': ('Ligue 1', 'Franca'),
            'N1': ('Eredivisie', 'Holanda'),
            'B1': ('Pro League', 'Belgica'),
            'P1': ('Primeira Liga', 'Portugal'),
            'T1': ('Super Lig', 'Turquia'),
            'G1': ('Super League', 'Grecia'),
            'DNK': ('Superliga', 'Dinamarca'),
            'BRA': ('Brasileirao', 'Brasil'),
            'ARG': ('Liga Profesional', 'Argentina'),
            'AUT': ('Bundesliga', 'Austria'),
            'SWZ': ('Super League', 'Suica'),
            'CZE': ('First League', 'Republica Tcheca'),
        }

        if division:
            if division in LEAGUE_MAPPING:
                league_name, country = LEAGUE_MAPPING[division]
                self.stdout.write(f"Divisão '{division}' detectada. Usando Liga: {league_name}, País: {country}")
            else:
                self.stdout.write(self.style.ERROR(f"Divisão '{division}' não encontrada no mapeamento."))
                return

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
            self.recalculate_for_league(league, season_year)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao buscar liga: {e}"))
            return

    def recalculate_for_league(self, league, season_year=None):
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
                self.stdout.write(self.style.ERROR(f"Nenhuma temporada com jogos encontrada para a liga {league.name}"))
                return

        self.stdout.write(
            self.style.SUCCESS(
                f"Recalculando tabela para {league.name}, temporada {season.year}"
            )
        )

        finished_matches = Match.objects.filter(
            league=league,
            season=season,
            status__in=["Finished", "FT", "AET", "PEN"],
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
