import json
import traceback
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season
from django.db import transaction

class Command(BaseCommand):
    help = "Lê um payload.json do SofaScore e processa nativamente no banco de dados de produção (Proxy Architecture)."

    def add_arguments(self, parser):
        parser.get_default('file')
        parser.add_argument('--file', type=str, default='payload.json', help='Caminho do payload JSON')
        parser.add_argument('--league_id', type=int, help='ID primário da Liga no MySQL de Produção')
        parser.add_argument('--season_id', type=int, help='ID primário da Season no MySQL de Produção')
        parser.add_argument('--league_name', type=str, help='Nome da Liga (Alternativa ao ID)')
        parser.add_argument('--country', type=str, help='País da Liga (Opcional)')
        parser.add_argument('--season_year', type=int, help='Ano da Temporada (Alternativa ao ID)')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file']
        league_db_id = kwargs['league_id']
        season_db_id = kwargs['season_id']

        self.stdout.write(f"Iniciando importação via Proxy Payload para Liga ID={league_db_id}, Temporada ID={season_db_id}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao ler {file_path}: {e}"))
            return

        try:
            if league_db_id:
                league = League.objects.get(id=league_db_id)
            elif kwargs.get('league_name'):
                name = kwargs['league_name']
                country = kwargs.get('country')
                if country:
                    league = League.objects.get(name=name, country=country)
                else:
                    league = League.objects.get(name=name)
            else:
                self.stdout.write(self.style.ERROR("Você deve fornecer --league_id ou --league_name"))
                return

            if season_db_id:
                season = Season.objects.get(id=season_db_id)
            elif kwargs.get('season_year'):
                season = Season.objects.get(year=kwargs['season_year'])
            else:
                # Fallback: pega a última season se não especificado
                season = Season.objects.all().order_by("-year").first()
                
            self.stdout.write(self.style.SUCCESS(f"Usando Liga: {league.name} (ID: {league.id}) e Temporada: {season.year} (ID: {season.id})"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro fatal: Liga ou Season não encontradas! {e}"))
            return

        standings_data = payload.get('standings')
        rounds_data = payload.get('rounds', [])

        teams_map = {} # SofaScore ID -> Team Object
        
        # 1. Obter e sincronizar Times (pode haver múltiplos grupos de standings)
        self.stdout.write("Sincronizando times nativamente...")
        if standings_data and 'standings' in standings_data:
            for group in standings_data['standings']:
                standings_list = group.get('rows', [])
                for row in standings_list:
                    team_data = row.get('team', {})
                    team_id = str(team_data.get('id'))
                    team_name = team_data.get('name')
                    
                    if league.name == "Ligue 1":
                        mapping = {
                            "Paris Saint-Germain": "PSG",
                            "Paris Saint-Germain FC": "PSG",
                            "AS Monaco": "Monaco",
                            "AS Monaco FC": "Monaco",
                            "Olympique Lyonnais": "Lyon",
                            "Olympique de Marseille": "Marseille",
                            "Lille OSC": "Lille",
                            "Stade Rennais": "Rennes",
                            "OGC Nice": "Nice",
                            "RC Lens": "Lens",
                            "Stade de Reims": "Reims",
                            "Reims": "Reims",
                            "Stade Brestois": "Brest",
                            "Stade Brestois 29": "Brest",
                            "Toulouse FC": "Toulouse",
                            "Montpellier HSC": "Montpellier",
                            "RC Strasbourg Alsace": "Strasbourg",
                            "FC Nantes": "Nantes",
                            "Le Havre AC": "Le Havre",
                            "Angers SCO": "Angers",
                            "AJ Auxerre": "Auxerre",
                            "FC Lorient": "Lorient",
                            "AS Saint-Étienne": "St Etienne",
                        }
                        team_name = mapping.get(team_name, team_name)
                    
                    
                    if team_id and team_name:
                        sofa_api_id = f"sofa_{team_id}"
                        # 1. Tenta por API ID
                        team = Team.objects.filter(api_id=sofa_api_id).first()
                        
                        # 2. Se não achou por API_ID, tenta por nome na mesma liga
                        if not team:
                            team = Team.objects.filter(name=team_name, league=league).first()
                            if team and not team.api_id:
                                team.api_id = sofa_api_id
                                team.save()
                        
                        # 3. Cria se não existir nada
                        if not team:
                            team = Team.objects.create(
                                api_id=sofa_api_id,
                                name=team_name,
                                league=league
                            )
                                
                        teams_map[int(team_id)] = team
                    
            self.stdout.write(self.style.SUCCESS(f"{len(teams_map)} times carregados/sincronizados no total."))
        else:
            self.stdout.write(self.style.ERROR("Nenhum dado de classificação (standings) encontrado no payload."))
            return

        # 2. Iterar Partidas
        matches_created = 0
        matches_updated = 0

        self.stdout.write(f"Processando blocos de rodadas ({len(rounds_data)} blocos mapeados)...")
        
        for round_block in rounds_data:
            round_number = round_block.get('round_number')
            round_label = round_block.get('round_label', 'Round')
            events = round_block.get('events', [])
            
            with transaction.atomic():
                for ev in events:
                    fixture_id = str(ev.get('id'))
                    match_api_id = f"sofa_{fixture_id}"
                    
                    home_data = ev.get('homeTeam', {})
                    away_data = ev.get('awayTeam', {})
                    home_sofa_id = home_data.get('id')
                    away_sofa_id = away_data.get('id')
                    
                    start_timestamp = ev.get('startTimestamp')
                    match_date = datetime.fromtimestamp(start_timestamp, tz=timezone.utc) if start_timestamp else None
                    
                    status_type = ev.get('status', {}).get('type')
                    
                    match_status = "Scheduled"
                    if status_type == 'finished':
                        match_status = "FT"
                    elif status_type == 'inprogress':
                        match_status = "In Play"
                    elif status_type == 'canceled':
                        match_status = "Cancelled"
                    elif status_type == 'postponed':
                        match_status = "Postponed"
                    
                    home_score = ev.get('homeScore', {}).get('current')
                    away_score = ev.get('awayScore', {}).get('current')
                    
                    home_team = teams_map.get(int(home_sofa_id))
                    away_team = teams_map.get(int(away_sofa_id))
                    
                    if not home_team or not away_team:
                        continue
                    
                    # Deduplicação Inteligente
                    # 1. Tenta por API_ID
                    match = Match.objects.filter(api_id=match_api_id).first()
                    
                    # 2. Tenta por Times e Data (mesmo dia)
                    if not match and match_date:
                        match = Match.objects.filter(
                            home_team=home_team,
                            away_team=away_team,
                            date__date=match_date.date()
                        ).first()
                        
                    if match:
                        created = False
                        match.api_id = match_api_id # Garante que agora tem o ID do SofaScore
                        match.league = league
                        match.season = season
                        match.home_team = home_team
                        match.away_team = away_team
                        match.date = match_date
                        match.round_name = f"{round_label} - Round {round_number}"
                        match.status = match_status
                        match.home_score = home_score
                        match.away_score = away_score
                        match.save()
                    else:
                        match = Match.objects.create(
                            api_id=match_api_id,
                            league=league,
                            season=season,
                            home_team=home_team,
                            away_team=away_team,
                            date=match_date,
                            round_name=f"{round_label} - Round {round_number}",
                            status=match_status,
                            home_score=home_score,
                            away_score=away_score
                        )
                        created = True
                    
                    if created: matches_created += 1
                    else: matches_updated += 1
                        
        self.stdout.write(self.style.SUCCESS(f"Importação completa! {matches_created} partidas criadas, {matches_updated} atualizadas."))
                        
        self.stdout.write(self.style.SUCCESS(f"Importação completa! {matches_created} partidas criadas, {matches_updated} atualizadas com segurança."))
