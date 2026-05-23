"""
Exporta dados do Deep Scrape (estatísticas avançadas + gols) para JSON.

Uso:
  python manage.py export_deep_scrape
  python manage.py export_deep_scrape --liga 7
  python manage.py export_deep_scrape --liga 7 --output bundesliga.json
  python manage.py export_deep_scrape --todas
"""
import json
import os
from django.core.management.base import BaseCommand
from django.db.models import Count
from matches.models import Match, Goal


class Command(BaseCommand):
    help = "Exporta dados do Deep Scrape (escanteios, cartões, chutes, gols) para JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            '--liga',
            type=int,
            default=None,
            help='ID da liga para exportar (ex: 7 para Bundesliga)'
        )
        parser.add_argument(
            '--todas',
            action='store_true',
            help='Exportar todas as ligas que têm dados de deep scrape'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='dados_deep_scrape.json',
            help='Arquivo de saída (padrão: dados_deep_scrape.json)'
        )

    def handle(self, *args, **options):
        league_id = options.get('liga')
        todas = options.get('todas', False)
        output_file = options.get('output', 'dados_deep_scrape.json')

        # Filtro base: partidas que passaram pelo deep scrape
        filters = {'home_corners__isnull': False}
        if league_id:
            filters['league_id'] = league_id
            league_name = self._get_league_name(league_id)
            self.stdout.write(f"📤 Exportando dados da liga: {league_name} (ID: {league_id})")
        elif not todas:
            # Se não especificou nada, mostra as ligas disponíveis
            self._list_available_leagues()
            return

        # Busca as partidas
        matches = Match.objects.filter(**filters).exclude(
            api_id__isnull=True
        ).exclude(api_id__exact='').select_related('league', 'season')

        total = matches.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("Nenhuma partida com deep scrape encontrada."))
            return

        self.stdout.write(f"📊 {total} partidas encontradas para exportar...")

        export_data = []
        for m in matches:
            match_data = {
                'api_id': m.api_id,
                'league_id': m.league_id,
                'league_name': m.league.name if m.league else None,
                'league_country': m.league.country if m.league else None,
                'season_year': m.season.year if m.season else None,
                'home_team': m.home_team.name if m.home_team else None,
                'away_team': m.away_team.name if m.away_team else None,
                'stats': {
                    'home_corners': m.home_corners,
                    'away_corners': m.away_corners,
                    'home_yellow': m.home_yellow,
                    'away_yellow': m.away_yellow,
                    'home_red': m.home_red,
                    'away_red': m.away_red,
                    'home_shots': m.home_shots,
                    'away_shots': m.away_shots,
                    'home_shots_on_target': m.home_shots_on_target,
                    'away_shots_on_target': m.away_shots_on_target,
                    'home_fouls': m.home_fouls,
                    'away_fouls': m.away_fouls,
                },
                'goals': []
            }

            # Pega os gols
            gols = Goal.objects.filter(match=m).select_related('team')
            for g in gols:
                # Descobre se é time da casa ou visitante pelo nome do time
                is_home = (g.team_id == m.home_team_id) if m.home_team_id and g.team_id else None
                match_data['goals'].append({
                    'player_name': g.player_name,
                    'minute': g.minute,
                    'is_own_goal': g.is_own_goal,
                    'is_penalty': g.is_penalty,
                    'team_name': g.team.name if g.team else None,
                    'is_home': is_home,
                })

            export_data.append(match_data)

        # Salva o JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        total_goals = sum(len(d['goals']) for d in export_data)
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Exportado para {output_file}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"   {total} partidas, {total_goals} gols"
        ))

        # Mostra resumo por liga
        from collections import Counter
        ligas = Counter((d['league_country'], d['league_name']) for d in export_data)
        self.stdout.write("\n📋 Resumo por liga:")
        for (pais, liga), qtd in sorted(ligas.items()):
            self.stdout.write(f"   {pais} - {liga}: {qtd} partidas")

    def _get_league_name(self, league_id):
        from matches.models import League
        league = League.objects.filter(id=league_id).first()
        return f"{league.country} - {league.name}" if league else f"ID {league_id}"

    def _list_available_leagues(self):
        """Mostra as ligas disponíveis para exportação."""
        from matches.models import League
        from django.db.models import Count
        
        leagues = League.objects.filter(
            matches__home_corners__isnull=False
        ).annotate(
            qtd=Count('matches')
        ).order_by('country', 'name')
        
        self.stdout.write(self.style.WARNING(
            "Especifique --liga ID ou --todas para exportar.\n"
        ))
        self.stdout.write("📋 Ligas com dados de Deep Scrape disponíveis:")
        self.stdout.write("-" * 60)
        
        for league in leagues:
            self.stdout.write(
                f"   ID {league.id:<3} | {league.country:<15} | {league.name:<25} | {league.qtd} partidas"
            )
        
        self.stdout.write("")
        self.stdout.write("Uso:")
        self.stdout.write("  python manage.py export_deep_scrape --liga 7")
        self.stdout.write("  python manage.py export_deep_scrape --todas")
        self.stdout.write(f"  python manage.py export_deep_scrape --todas --output dados.json")
