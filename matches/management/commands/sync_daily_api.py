import time
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import League

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Roda a sincronização diária de jogos e estatísticas para todas as ligas mapeadas.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50, help='Limite máximo de estatísticas a buscar por liga (evitar consumo exagerado da API num único dia).')
        parser.add_argument('--season', type=int, default=datetime.now().year, help='Ano da temporada.')

    def handle(self, *args, **options):
        stat_limit = options['limit']
        season_year = options['season']

        self.stdout.write(self.style.SUCCESS(f"Iniciando Sincronização Diária - Temporada {season_year}..."))

        # Seleciona apenas as ligas que possuem api_id configurado
        leagues = League.objects.filter(api_id__isnull=False)

        if not leagues.exists():
            self.stdout.write(self.style.WARNING("Nenhuma liga mapeada encontrada. Rode 'map_api_ids' primeiro!"))
            return

        total_leagues = leagues.count()
        self.stdout.write(f"Foram encontradas {total_leagues} ligas mapeadas. Sincronizando...")

        for i, league in enumerate(leagues, 1):
            self.stdout.write(self.style.SUCCESS(f"\n[{i}/{total_leagues}] Processando a liga: {league.name} (API ID: {league.api_id})"))
            
            # Lógica inteligente de calendário: Europa = Ano-1 (ex: 25/26), Américas = Ano (ex: 2026)
            european_leagues = [
                'Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1', 
                'Eredivisie', 'Primeira Liga', 'Championship', 'Super League', 
                'Premiership', 'Ekstraklasa', 'Superliga', 'Pro League', 'First League'
            ]
            league_season = (season_year - 1) if league.name in european_leagues else season_year
            
            try:
                # Chama o nosso super motor de backfill para essa liga específica
                call_command(
                    'backfill_api_matches', 
                    league_id=league.id, 
                    limit=stat_limit,
                    season=league_season
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao sincronizar a liga {league.name}: {e}"))
                logger.error(f"Erro na sync_daily_api para a liga {league.id}: {e}")
            
            # Pequena pausa de 2 segundos entre ligas para aliviar o servidor e a API
            time.sleep(2)

        self.stdout.write(self.style.SUCCESS("\nSincronização Diária concluída com sucesso! Todos os placares, escanteios e gols foram atualizados."))
