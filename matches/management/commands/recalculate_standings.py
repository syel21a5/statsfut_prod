import os
import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from matches.models import League, Season, Team, Match, LeagueStanding
from matches.api_manager import APIManager
from matches.utils_odds_api import resolve_team

class Command(BaseCommand):
    help = "Atualiza a tabela de classificação oficial via API-Football PRO"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Atualiza a tabela para todas as ligas mapeadas")
        parser.add_argument("--smart", action="store_true", help="Atualiza apenas ligas com jogos nas últimas 24h")
        parser.add_argument("--league_id", type=int, default=None, help="ID da liga na API-Football")

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando Atualização PRO de Classificação (Standings)"))
        
        api = APIManager()
        api_config = api.apis.get('api_football_1')
        
        if not api_config or not api_config.get('key'):
            self.stdout.write(self.style.ERROR("Chave API_FOOTBALL_KEY não encontrada. Abortando."))
            return
            
        base_url = api_config['base_url']
        headers = api._get_headers(api_config)
        
        target_leagues = []
        for l_name, l_data in api.LEAGUE_MAPPINGS.items():
            if l_data.get('api_football'):
                for api_id in l_data['api_football']:
                    if options['league_id'] and api_id != options['league_id']:
                        continue
                        
                    db_league = League.objects.filter(name__iexact=l_name).first()
                    if not db_league:
                        db_league = League.objects.filter(name__icontains=l_name).first()
                    if db_league:
                        target_leagues.append({'api_id': api_id, 'db_obj': db_league})

        if options["smart"]:
            yesterday = timezone.now() - timedelta(days=1)
            recent_league_ids = Match.objects.filter(date__gte=yesterday).values_list('league_id', flat=True).distinct()
            target_leagues = [l for l in target_leagues if l['db_obj'].id in recent_league_ids]
            
        if not target_leagues:
            self.stdout.write(self.style.WARNING("Nenhuma liga para processar."))
            return

        season_year = timezone.now().year
        db_season, _ = Season.objects.get_or_create(year=season_year)

        for league_data in target_leagues:
            api_league_id = league_data['api_id']
            db_league = league_data['db_obj']
            
            self.stdout.write(f"\n--> Buscando Standings para: {db_league.name} (API ID: {api_league_id})")
            
            url = f"{base_url}/standings"
            params = {'league': api_league_id, 'season': season_year}
            
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                api._increment_usage('api_football_1')
                
                if resp.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"Erro na API: {resp.text}"))
                    continue
                    
                data = resp.json().get('response', [])
                if not data:
                    self.stdout.write(self.style.WARNING("Sem dados de classificação para esta temporada."))
                    continue
                
                standings_groups = data[0]['league']['standings']
                
                with transaction.atomic():
                    # Deletar antigas classificações para esta liga e temporada
                    LeagueStanding.objects.filter(league=db_league, season=db_season).delete()
                    
                    standings_to_create = []
                    
                    for group in standings_groups:
                        for row in group:
                            rank = row['rank']
                            points = row['points']
                            goals_diff = row['goalsDiff']
                            group_name = row['group']
                            
                            all_stats = row['all']
                            played = all_stats['played']
                            won = all_stats['win']
                            drawn = all_stats['draw']
                            lost = all_stats['lose']
                            gf = all_stats['goals']['for']
                            ga = all_stats['goals']['against']
                            
                            team_name = row['team']['name']
                            db_team = resolve_team(team_name, db_league)
                            
                            if not db_team:
                                continue
                                
                            standings_to_create.append(LeagueStanding(
                                league=db_league,
                                season=db_season,
                                team=db_team,
                                position=rank,
                                played=played,
                                won=won,
                                drawn=drawn,
                                lost=lost,
                                goals_for=gf,
                                goals_against=ga,
                                points=points,
                                group_name=group_name
                            ))
                            
                    LeagueStanding.objects.bulk_create(standings_to_create)
                    self.stdout.write(self.style.SUCCESS(f"Tabela de {db_league.name} atualizada com {len(standings_to_create)} times."))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro: {e}"))
                
        self.stdout.write(self.style.SUCCESS("Processo Concluído!"))
