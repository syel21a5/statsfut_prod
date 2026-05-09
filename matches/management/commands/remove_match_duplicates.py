from django.core.management.base import BaseCommand
from django.db.models import Count
from matches.models import Match, League, Season


class Command(BaseCommand):
    help = "Remove jogos duplicados (mesma data, mandante e visitante)"

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

        # Fase 1: Remover matches órfãos (sem time)
        orphan_home = qs.filter(home_team__isnull=True).count()
        orphan_away = qs.filter(away_team__isnull=True).count()
        qs.filter(home_team__isnull=True).delete()
        qs.filter(away_team__isnull=True).delete()
        if orphan_home or orphan_away:
            self.stdout.write(f"Removidos {orphan_home + orphan_away} jogos órfãos (sem time).")

        # Fase 2: Duplicatas EXATAS (mesma data E hora, mesmos times)
        # Isso pega registros que são realmente o mesmo jogo importado duas vezes
        duplicates_strict = (
            qs.values("date", "home_team", "away_team")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )
        
        count_strict = 0
        total_items = duplicates_strict.count()
        self.stdout.write(f"Encontrados {total_items} grupos de duplicatas exatas (data+hora/home/away).")

        for i, item in enumerate(duplicates_strict):
            if i % 100 == 0 and i > 0:
                self.stdout.write(f"Processando grupo {i}/{total_items}...")
            matches = qs.filter(
                date=item["date"],
                home_team=item["home_team"],
                away_team=item["away_team"],
            ).order_by("-api_id", "-id")
            
            # Mantém o primeiro (melhor), deleta o resto
            for m in matches[1:]:
                m.delete()
                count_strict += 1
                
        self.stdout.write(f"Removidas {count_strict} duplicatas exatas.")

        # =====================================================================
        # SEGURANÇA: NÃO DELETAR jogos apenas por season+home+away!
        # Em ligas com playoffs (Suíça, Áustria, Bélgica), os mesmos times
        # se enfrentam MAIS DE UMA VEZ na mesma temporada.
        # A Fase 2 acima já garante que jogos com a MESMA DATA+HORA são
        # tratados como duplicatas reais. Jogos em datas diferentes são
        # partidas LEGÍTIMAS (fase regular vs playoff).
        # =====================================================================

        self.stdout.write(self.style.SUCCESS(
            f"Limpeza concluída. Removidos {count_strict} jogos duplicados. "
            f"Jogos de playoff preservados com segurança."
        ))
