"""
Importa partidas completas de um JSON exportado.

Uso:
  python manage.py import_full_matches partidas_sulamericana.json
  python manage.py import_full_matches partidas_sulamericana.json --dry-run
"""
import json
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from matches.models import Match, Team, Season, League


class Command(BaseCommand):
    help = "Importa partidas completas (incluindo times, api_id, stats)"

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Arquivo JSON')
        parser.add_argument('--dry-run', action='store_true', help='Apenas simular')

    def handle(self, *args, **options):
        json_file = options['json_file']
        dry_run = options.get('dry_run', False)

        if not os.path.exists(json_file):
            self.stdout.write(self.style.ERROR(f'Arquivo {json_file} não encontrado!'))
            return

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.stdout.write(f'📥 Importando {len(data)} partidas...')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 Modo DRY-RUN\n'))

        created = 0
        updated = 0
        skipped = 0

        for item in data:
            api_id = item['api_id']
            if not api_id:
                skipped += 1
                continue

            league = League.objects.filter(id=item['league_id']).first()
            if not league:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Liga ID {item["league_id"]} não encontrada!'))
                skipped += 1
                continue

            season = Season.objects.get_or_create(id=item['season_id'])[0]
            if not season:
                season = Season.objects.get_or_create(year=2026)[0]

            # Busca ou cria times
            home_team = self._get_team(item['home_team_name'], league, item.get('home_team_api_id'))
            away_team = self._get_team(item['away_team_name'], league, item.get('away_team_api_id'))

            if not home_team or not away_team:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Times não encontrados: {item["home_team_name"]} x {item["away_team_name"]}'))
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f'  📋 {item["home_team_name"]} x {item["away_team_name"]} (api_id: {api_id})')
                continue

            # Cria ou atualiza a partida
            match, was_created = Match.objects.update_or_create(
                api_id=api_id,
                defaults={
                    'league': league,
                    'season': season,
                    'home_team': home_team,
                    'away_team': away_team,
                    'date': item.get('date'),
                    'status': item.get('status', 'Scheduled'),
                    'home_score': item.get('home_score'),
                    'away_score': item.get('away_score'),
                    'home_corners': item.get('home_corners'),
                    'away_corners': item.get('away_corners'),
                    'home_yellow': item.get('home_yellow'),
                    'away_yellow': item.get('away_yellow'),
                    'home_red': item.get('home_red'),
                    'away_red': item.get('away_red'),
                    'home_shots': item.get('home_shots'),
                    'away_shots': item.get('away_shots'),
                    'home_shots_on_target': item.get('home_shots_on_target'),
                    'away_shots_on_target': item.get('away_shots_on_target'),
                    'home_fouls': item.get('home_fouls'),
                    'away_fouls': item.get('away_fouls'),
                }
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(f'\n{"="*50}')
        self.stdout.write(self.style.SUCCESS(f'✅ Importação concluída!'))
        self.stdout.write(f'   📝 Criadas: {created}')
        self.stdout.write(f'   🔄 Atualizadas: {updated}')
        self.stdout.write(f'   ⏭️  Puladas: {skipped}')

    def _get_team(self, team_name, league, api_id=None):
        """Busca ou cria time no banco."""
        # Tenta pelo api_id
        if api_id:
            team = Team.objects.filter(api_id=api_id).first()
            if team:
                return team

        # Tenta pelo nome + liga
        team = Team.objects.filter(name__iexact=team_name, league=league).first()
        if team:
            if api_id and not team.api_id:
                team.api_id = api_id
                team.save()
            return team

        # Tenta nome contido
        team = Team.objects.filter(name__icontains=team_name.split()[0], league=league).first()
        if team:
            if api_id and not team.api_id:
                team.api_id = api_id
                team.save()
            return team

        # Cria novo time
        team = Team.objects.create(
            name=team_name,
            league=league,
            api_id=api_id
        )
        self.stdout.write(self.style.WARNING(f'    🆕 Time criado: {team_name}'))
        return team
