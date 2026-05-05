import json
import traceback
from datetime import datetime, timezone
from django.core.management.base import BaseCommand  # type: ignore
from matches.models import League, Team, Match, Season, LeagueStanding  # type: ignore
from django.db import transaction  # type: ignore

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
            league = None
            if league_db_id:
                league = League.objects.get(id=league_db_id)
            elif kwargs.get('league_name'):
                league_name_arg = kwargs['league_name']
                country_arg = kwargs.get('country')
                
                # Flexibilidade na busca da liga
                # 1. Tenta busca exata (case-insensitive)
                if country_arg:
                    league = League.objects.filter(name__iexact=league_name_arg, country__iexact=country_arg).first()
                else:
                    league = League.objects.filter(name__iexact=league_name_arg).first()

                # 2. Se não encontrou e o país é relacionado à França, tenta variações
                if not league and country_arg and country_arg.lower() in ['franca', 'frança', 'france']:
                    for c_var in ['Franca', 'França', 'France']:
                        league = League.objects.filter(name__iexact=league_name_arg, country__iexact=c_var).first()
                        if league:
                            break
                
                if not league:
                    self.stdout.write(self.style.ERROR(f"Liga '{league_name_arg}' (País: '{country_arg or 'Não especificado'}') não encontrada."))
                    return
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
                    
                    # Normalização de Nomes para Ligue 1
                    is_france = league.name.lower() in ["ligue 1", "ligue 1 "] or league.country.lower() in ["franca", "frança", "france"]
                    
                    if is_france:
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
                    
                    is_brazil = league.name.lower() in ["brasileirão", "brasileirao", "serie a"] or league.country.lower() in ["brasil", "brazil"]
                    if is_brazil:
                        brazil_mapping = {
                            "Atlético Mineiro": "Atletico-MG",
                            "Vasco da Gama": "Vasco",
                            "Red Bull Bragantino": "Bragantino",
                            "Athletico Paranaense": "Athletico"
                        }
                        team_name = brazil_mapping.get(str(team_name), str(team_name))
                    
                    is_argentina = league.name.lower() in ["liga profesional", "copa de la liga"] or league.country.lower() in ["argentina"]
                    if is_argentina:
                        arg_mapping = {
                            "Estudiantes de La Plata": "Estudiantes L.P.",
                            "Vélez Sarsfield": "Velez Sarsfield",
                            "CA Talleres": "Talleres Cordoba",
                            "CA Lanús": "Lanus",
                            "CA Independiente": "Independiente",
                            "Club Atlético Unión de Santa Fe": "Union de Santa Fe",
                            "Instituto De Córdoba": "Instituto",
                            "Club Atlético Platense": "Platense",
                            "Gimnasia y Esgrima Mendoza": "Gimnasia Mendoza",
                            "Newell's Old Boys": "Newells Old Boys",
                            "Deportivo Riestra": "Dep. Riestra",
                            "Independiente Rivadavia": "Ind. Rivadavia",
                            "Argentinos Juniors": "Argentinos Jrs",
                            "Club Atlético Belgrano": "Belgrano",
                            "Gimnasia y Esgrima": "Gimnasia L.P.",
                            "Huracán": "Huracan",
                            "Atlético Tucumán": "Atl. Tucuman",
                            "Sarmiento": "Sarmiento Junin",
                            "Estudiantes de Río Cuarto": "Estudiantes Rio Cuarto",
                            "Central Córdoba": "Central Cordoba",
                        }
                        team_name = arg_mapping.get(team_name, team_name)

                    is_austria = league.name.lower() in ["bundesliga"] or league.country.lower() in ["austria"]
                    if is_austria:
                        aus_mapping = {
                            "Rapid Vienna": "Rapid Wien",
                            "SK Rapid Wien": "Rapid Wien",
                            "Austria Vienna": "Austria Wien",
                            "FK Austria Wien": "Austria Wien",
                            "Red Bull Salzburg": "Salzburg",
                            "FC Salzburg": "Salzburg",
                            "LASK": "LASK Linz",
                            "SV Ried": "Ried",
                            "WSG Tirol": "Tirol",
                            "Grazer AK 1902": "Grazer AK",
                            "GAK 1902": "Grazer AK",
                            "FC Blau-Weiß Linz": "FC Blau Weiß Linz",
                            "FC Blau Weiss Linz": "FC Blau Weiß Linz",
                            "SV Grödig": "SV Grodig",
                            "SK Sturm Graz": "Sturm Graz",
                            "Wolfsberger AC": "Wolfsberger AC",
                            "CASHPOINT SCR Altach": "Altach",
                            "SCR Altach": "Altach",
                            "SC Rheindorf Altach": "Altach",
                            "TSV Hartberg": "Hartberg",
                        }
                        team_name = aus_mapping.get(team_name, team_name)
                    
                    # Limpeza extra
                    team_name = (team_name or '').strip()
                    if team_id and team_name:
                        sofa_api_id = f"sofa_{team_id}"
                        try:
                            # 1. Tenta por API ID
                            team = Team.objects.filter(api_id=sofa_api_id).first()
                            if team:
                                changed = False
                                if team.name != team_name:
                                    team.name = team_name
                                    changed = True
                                if changed:
                                    team.save()
                            
                            # 2. Se não achou por API_ID, tenta por nome na mesma liga
                            if not team:
                                team = Team.objects.filter(name=team_name, league=league).first()
                                if team and not team.api_id:
                                    team.api_id = sofa_api_id
                                    if team.name != team_name:
                                        team.name = team_name
                                    team.save()
                            
                            # 3. Cria se não existir nada
                            if not team:
                                team = Team.objects.create(
                                    api_id=sofa_api_id,
                                    name=team_name,
                                    league=league
                                )
                                    
                            teams_map[int(team_id)] = team
                        except Exception as te:
                            self.stdout.write(self.style.WARNING(f"Erro ao sincronizar time {team_name} ({team_id}): {te}"))
                            # Tenta fallback por nome se API ID falhou
                            team = Team.objects.filter(name=team_name, league=league).first()
                            if team:
                                teams_map[int(team_id)] = team
                    
            self.stdout.write(self.style.SUCCESS(f"{len(teams_map)} times carregados/sincronizados no total."))
            
            # 1.5. Salvar a Classificação (Standings) Perfeita do SofaScore
            # EXCEÇÃO: A Argentina (Liga Profesional) possui um layout e um motor
            # de recálculo customizados (Grupos A/B/Promedios). Não importamos a tabela bruta.
            if league.country == 'Argentina' and 'profesional' in league.name.lower():
                self.stdout.write(self.style.WARNING("Pulando importação de classificação para a Argentina (regras customizadas)."))
            else:
                self.stdout.write("Importando Classificações exatas do SofaScore...")
                with transaction.atomic():
                    # Remove as classificações antigas para esta liga/temporada para evitar sujeira
                    LeagueStanding.objects.filter(league=league, season=season).delete()
                    
                    standings_saved = 0
                    for group in standings_data['standings']:
                        group_name = group.get('name', 'Regular Season')
                        standings_list = group.get('rows', [])
                        for row in standings_list:
                            team_id = str(row.get('team', {}).get('id'))
                            team = teams_map.get(int(team_id)) if team_id.isdigit() else None
                            
                            if team:
                                LeagueStanding.objects.create(
                                    league=league,
                                    season=season,
                                    team=team,
                                    group_name=group_name,
                                    position=row.get('position', 0),
                                    played=row.get('matches', 0),
                                    won=row.get('wins', 0),
                                    drawn=row.get('draws', 0),
                                    lost=row.get('losses', 0),
                                    goals_for=row.get('scoresFor', 0),
                                    goals_against=row.get('scoresAgainst', 0),
                                    points=row.get('points', 0)
                                )
                                standings_saved += 1
                                
                    self.stdout.write(self.style.SUCCESS(f"{standings_saved} posições de classificação salvas com sucesso em seus respectivos grupos."))

                
        else:
            self.stdout.write(self.style.ERROR("Nenhum dado de classificação (standings) encontrado no payload."))

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
                    # Half-time scores (period1 = first half in SofaScore API)
                    ht_home_score = ev.get('homeScore', {}).get('period1')
                    ht_away_score = ev.get('awayScore', {}).get('period1')
                    
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
                        # Só atualiza HT se tiver dados (não sobrescreve dados existentes com None)
                        if ht_home_score is not None:
                            match.ht_home_score = ht_home_score
                        if ht_away_score is not None:
                            match.ht_away_score = ht_away_score
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
                            away_score=away_score,
                            ht_home_score=ht_home_score,
                            ht_away_score=ht_away_score,
                        )
                        created = True
                    
                    if created: matches_created += 1
                    else: matches_updated += 1
                        
        self.stdout.write(self.style.SUCCESS(f"Importação completa! {matches_created} partidas criadas, {matches_updated} atualizadas."))
                        
        self.stdout.write(self.style.SUCCESS(f"Importação completa! {matches_created} partidas criadas, {matches_updated} atualizadas com segurança."))
