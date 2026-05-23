"""
Exporta partidas completas (incluindo times e api_id) de uma liga específica.
Útil para sincronizar servidor com local quando as partidas não existem no servidor.

Uso:
  python manage.py export_full_matches --liga 53
  python manage.py export_full_matches --liga 53 --output partidas_sulamericana.json
"""
import json
import os
from django.core.management.base import BaseCommand
from matches.models import Match, Team, Season, League


class Command(BaseCommand):
    help = "Exporta partidas completas (times, api_id, data) de uma liga"

    def add_arguments(self, parser):
        parser.add_argument('--liga', type=int, required=True, help='ID da liga')
        parser.add_argument('--output', type=str, default='partidas_export.json')
        parser.add_argument('--season-year', type=int, default=None, help='Ano da temporada (padrão: 2026)')

    def handle(self, *args, **options):
        league_id = options['liga']
        output_file = options['output']
        season_year = options.get('season_year')

        league = League.objects.filter(id=league_id).first()
        if not league:
            self.stdout.write(self.style.ERROR(f'Liga ID {league_id} não encontrada!'))
            return

        # Pega a temporada mais recente que tem partidas
        seasons = Season.objects.filter(matches__league=league).distinct().order_by('-year')
        if season_year:
            seasons = seasons.filter(year=season_year)
        
        if not seasons:
            self.stdout.write(self.style.ERROR(f'Nenhuma temporada encontrada para {league.name}'))
            return
            
        season = seasons.first()
        self.stdout.write(f'📅 Temporada: {season.year} (ID: {season.id})')

        self.stdout.write(f'📤 Exportando partidas de {league.country} - {league.name}...')

        matches = Match.objects.filter(
            league=league,
            season=season,
            api_id__isnull=False
        ).exclude(api_id__exact='').select_related('home_team', 'away_team')

        total = matches.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('Nenhuma partida com api_id encontrada.'))
            return

        export_data = []
        for m in matches:
            export_data.append({
                'api_id': m.api_id,
                'league_id': m.league_id,
                'season_id': m.season_id,
                'home_team_name': m.home_team.name if m.home_team else '?',
                'away_team_name': m.away_team.name if m.away_team else '?',
                'home_team_api_id': m.home_team.api_id if m.home_team else None,
                'away_team_api_id': m.away_team.api_id if m.away_team else None,
                'date': m.date.isoformat() if m.date else None,
                'status': m.status,
                'home_score': m.home_score,
                'away_score': m.away_score,
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
            })

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f'✅ {total} partidas exportadas para {output_file}'
        ))

    def _get_team(self, team_id):
        return Team.objects.filter(id=team_id).first()
