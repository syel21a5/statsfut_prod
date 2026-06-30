from django.core.management.base import BaseCommand
from django.db.models import Q, Count
from matches.models import Match, Team, League, Season, LeagueStanding

FINISHED_STATUSES = ['Finished', 'FT', 'AET', 'PEN', 'FINISHED']


class Command(BaseCommand):
    help = 'Diagnostica problemas de times e jogos no Brasileirao'

    def add_arguments(self, parser):
        parser.add_argument('--league', type=str, default='Brasileirão', help='Nome da liga')

    def handle(self, *args, **options):
        league_name = options['league']
        league = League.objects.filter(name__iexact=league_name).first()
        
        if not league:
            self.stdout.write(self.style.ERROR(f"Liga '{league_name}' nao encontrada."))
            return
        
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(f"  DIAGNOSTICO: {league.name} (ID: {league.id}, API: {league.api_id})")
        self.stdout.write(f"{'='*70}\n")

        # 1. Qual season a view usa?
        latest_season = Season.objects.filter(standings__league=league).order_by('-year').distinct().first()
        self.stdout.write(f"[1] Season usada pela view: {latest_season} (ID: {latest_season.id if latest_season else 'N/A'}, year: {latest_season.year if latest_season else 'N/A'})")
        
        # 2. Quais seasons existem nos matches?
        match_seasons = Match.objects.filter(league=league).values_list('season', flat=True).distinct()
        season_ids = list(match_seasons)
        self.stdout.write(f"[2] Seasons nos matches: {season_ids}")
        
        for sid in season_ids:
            s = Season.objects.filter(id=sid).first()
            count = Match.objects.filter(league=league, season_id=sid).count()
            self.stdout.write(f"    - Season ID {sid} (year={s.year if s else '?'}): {count} jogos")

        # 3. Times na liga
        teams = Team.objects.filter(league=league).order_by('name')
        self.stdout.write(f"\n[3] Times cadastrados na liga: {teams.count()}")
        
        # 4. Para cada time, quantos jogos finalizados COM escanteios
        self.stdout.write(f"\n[4] JOGOS POR TIME (season={latest_season.year if latest_season else 'N/A'}):")
        self.stdout.write(f"{'Time':<30} {'Total':>6} {'Finish':>7} {'c/Esc':>6} {'s/Esc':>6} {'API_ID':>10}")
        self.stdout.write(f"{'-'*30} {'-'*6} {'-'*7} {'-'*6} {'-'*6} {'-'*10}")
        
        problem_teams = []
        
        for team in teams:
            all_m = Match.objects.filter(
                league=league, season=latest_season
            ).filter(Q(home_team=team) | Q(away_team=team))
            
            total = all_m.count()
            finished = all_m.filter(status__in=FINISHED_STATUSES).count()
            with_corners = all_m.filter(status__in=FINISHED_STATUSES).exclude(home_corners__isnull=True).count()
            without_corners = finished - with_corners
            
            marker = ""
            if total == 0:
                marker = " <-- SEM JOGOS"
                problem_teams.append(team)
            elif with_corners == 0 and finished > 0:
                marker = " <-- SEM ESCANTEIOS"
                problem_teams.append(team)
            elif with_corners < finished:
                marker = f" <-- FALTAM {without_corners}"
            
            self.stdout.write(f"{team.name:<30} {total:>6} {finished:>7} {with_corners:>6} {without_corners:>6} {str(team.api_id):>10}{marker}")

        # 5. Verificar times duplicados (mesmo nome, ligas diferentes)
        self.stdout.write(f"\n[5] TIMES DUPLICADOS (mesmo nome em ligas diferentes):")
        for team in teams:
            dupes = Team.objects.filter(name__iexact=team.name).exclude(id=team.id)
            if dupes.exists():
                for d in dupes:
                    self.stdout.write(f"  {team.name}: ID={team.id} (Liga: {team.league.name}) vs ID={d.id} (Liga: {d.league.name if d.league else 'N/A'})")

        # 6. Resumo de problemas
        if problem_teams:
            self.stdout.write(self.style.WARNING(f"\n[6] RESUMO DE PROBLEMAS: {len(problem_teams)} times com dados incompletos:"))
            for t in problem_teams:
                # Verificar se existem jogos com esse time em QUALQUER season
                any_matches = Match.objects.filter(
                    league=league
                ).filter(Q(home_team=t) | Q(away_team=t)).count()
                self.stdout.write(f"  - {t.name} (ID:{t.id}, API:{t.api_id}): 0 jogos na season atual, {any_matches} em todas as seasons")
        else:
            self.stdout.write(self.style.SUCCESS(f"\n[6] Todos os times estao OK."))
        
        self.stdout.write(f"\n{'='*70}")
