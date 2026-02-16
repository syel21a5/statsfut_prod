from django.core.management.base import BaseCommand
from django.db.models import Count
from matches.models import Match, League, Season

class Command(BaseCommand):
    help = "Remove jogos duplicados (mesma temporada, mandante e visitante)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--league_name",
            type=str,
            default=None,
            help="Nome da liga para filtrar (opcional)",
        )
        parser.add_argument(
            "--country",
            type=str,
            default=None,
            help="País da liga para filtrar (opcional)",
        )
        parser.add_argument(
            "--season_year",
            type=int,
            default=None,
            help="Ano da temporada para filtrar (opcional)",
        )

    def handle(self, *args, **options):
        league_name = options.get("league_name")
        country = options.get("country")
        season_year = options.get("season_year")

        qs = Match.objects.all()

        if league_name:
            league_filters = {"name": league_name}
            if country:
                league_filters["country"] = country
            leagues = League.objects.filter(**league_filters)
            qs = qs.filter(league__in=leagues)

        if season_year:
            seasons = Season.objects.filter(year=season_year)
            qs = qs.filter(season__in=seasons)

        qs.filter(home_team__isnull=True).delete()
        qs.filter(away_team__isnull=True).delete()

        duplicates_strict = (
            qs.values("date", "home_team", "away_team")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )
        
        count_strict = 0
        total_items = duplicates_strict.count()
        self.stdout.write(f"Encontrados {total_items} grupos de duplicatas exatas (data/home/away).")

        for i, item in enumerate(duplicates_strict):
            if i % 100 == 0:
                self.stdout.write(f"Processando grupo {i}/{total_items}...")
            matches = qs.filter(
                date=item["date"],
                home_team=item["home_team"],
                away_team=item["away_team"],
            ).order_by("-api_id", "-id")
            
            # Mantém o primeiro, deleta o resto
            for m in matches[1:]:
                m.delete()
                count_strict += 1
                
        self.stdout.write(f"Removidas {count_strict} duplicatas exatas.")

        duplicates = (
            qs.values("season", "home_team", "away_team")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )

        total_groups = duplicates.count()
        total_deleted = 0
        
        self.stdout.write(f"Encontrados {total_groups} confrontos duplicados (mesma temporada/mandante/visitante).")

        for item in duplicates:
            matches = qs.filter(
                season=item["season"],
                home_team=item["home_team"],
                away_team=item["away_team"],
            )
            
            # Critério de desempate para manter o "melhor" jogo:
            # 1. Tem API ID (veio da API paga/oficial)
            # 2. Tem status 'Finished'
            # 3. Tem placar (home_score não é nulo)
            # 4. Data mais recente (assumindo correção)
            # 5. ID maior (último inserido)
            
            sorted_matches = sorted(matches, key=lambda m: (
                1 if m.api_id else 0,
                1 if m.status == 'Finished' else 0,
                1 if m.home_score is not None else 0,
                m.date,
                m.id
            ), reverse=True)
            
            keep = sorted_matches[0]
            delete_list = sorted_matches[1:]
            
            for m in delete_list:
                self.stdout.write(f"Removendo duplicata: {m.home_team} vs {m.away_team} ({m.date}) [ID: {m.id}]")
                m.delete()
                total_deleted += 1
                
        self.stdout.write(self.style.SUCCESS(f"Limpeza concluída. Removidos {total_deleted} jogos duplicados."))
