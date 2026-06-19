import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import League, Match, Season, Team
from matches.api_manager import APIManager
from matches.team_validation import is_team_valid_for_league

# ============================================================================
# BLACKLIST: Times que a API-Football retorna incorretamente para certas ligas.
# Chave = api_id da liga na API-Football
# Valor = set de api_ids de times que NUNCA devem ser criados/associados a essa liga
#
# Exemplo real: A API retorna "Ath Bilbao" (API ID 531) em fixtures da Série B
# do Brasil (API ID 72), o que é um bug da API.
# ============================================================================
LEAGUE_TEAM_BLACKLIST = {
    # Série B do Brasil (api_id=72) - times europeus que aparecem por bug da API
    '72': {'531', '529', '530', '532', '533'},  # 531=Ath Bilbao, 529=Barcelona, 530=Atletico Madrid, etc.
    # Série A do Brasil (api_id=71)
    '71': {'531', '529', '530', '532', '533'},
}

# Blacklist por NOME de time (fallback caso o api_id mude)
LEAGUE_TEAM_NAME_BLACKLIST = {
    '72': {'ath bilbao', 'athletic bilbao', 'athletic club', 'barcelona', 'atletico madrid',
           'real madrid', 'sevilla', 'valencia', 'real betis', 'villarreal', 'real sociedad'},
    '71': {'ath bilbao', 'athletic bilbao', 'athletic club', 'barcelona', 'atletico madrid',
           'real madrid', 'sevilla', 'valencia', 'real betis', 'villarreal', 'real sociedad'},
}


class Command(BaseCommand):
    help = 'Busca fixtures e estatísticas passadas (Estratégia 1 - Otimizada) evitando chamadas redundantes.'

    def add_arguments(self, parser):
        parser.add_argument('--league_id', type=int, required=True, help='ID da liga no banco de dados local.')
        parser.add_argument('--limit', type=int, default=10, help='Limite de chamadas individuais de estatísticas (para economizar cota). Use 0 para ilimitado.')
        parser.add_argument('--season', type=int, default=datetime.now().year, help='Ano da temporada (ex: 2024). Padrão é o ano atual.')

    def handle(self, *args, **options):
        league_id_db = options['league_id']
        stat_limit = options['limit']
        season_year = options['season']

        try:
            db_league = League.objects.get(id=league_id_db)
        except League.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Liga ID {league_id_db} não encontrada no banco."))
            return

        if not db_league.api_id:
            self.stdout.write(self.style.ERROR(f"A Liga '{db_league.name}' não possui api_id. Mapeie primeiro!"))
            return

        api = APIManager()
        api_config = api.apis.get('api_football_1')
        if not api_config or not api_config.get('key'):
            self.stdout.write(self.style.ERROR("API_FOOTBALL_KEY não encontrada."))
            return

        headers = api._get_headers(api_config)
        base_url = api_config['base_url']
        
        db_season, _ = Season.objects.get_or_create(year=season_year)

        self.stdout.write(self.style.SUCCESS(f"\n[1] Buscando fixtures da Liga '{db_league.name}' (Temporada {season_year})..."))
        
        # 1. Buscar todos os jogos (Fixtures) da Liga (Gasta apenas 1 crédito)
        params = {'league': db_league.api_id, 'season': season_year}
        try:
            resp = api._make_request(f"{base_url}/fixtures", headers=headers, params=params, timeout=15)
            api._increment_usage('api_football_1')
            
            data_json = resp.json()
            if 'errors' in data_json and data_json['errors']:
                self.stdout.write(self.style.ERROR(f"Erro da API: {data_json['errors']}"))
                return
                
            fixtures = data_json.get('response', [])
            if not fixtures:
                self.stdout.write(self.style.WARNING("Nenhuma partida retornada pela API."))
                return
                
            self.stdout.write(f"Recebidos {len(fixtures)} jogos. Atualizando banco de dados...")
            
            # Atualiza placares gerais de forma massiva
            matched_count = 0
            for fix in fixtures:
                f_id = str(fix['fixture']['id'])
                f_status = fix['fixture']['status']['short']
                home_goals = fix['goals'].get('home')
                away_goals = fix['goals'].get('away')
                home_api_id = str(fix['teams']['home']['id'])
                away_api_id = str(fix['teams']['away']['id'])
                home_name = fix['teams']['home']['name']
                away_name = fix['teams']['away']['name']
                f_date_str = fix['fixture'].get('date', '')
                round_name = fix.get('league', {}).get('round', '')
                
                # ============================================================
                # BLACKLIST CHECK: Pula fixtures com times que não pertencem à liga
                # ============================================================
                league_api_str = str(db_league.api_id)
                bl_ids = LEAGUE_TEAM_BLACKLIST.get(league_api_str, set())
                bl_names = LEAGUE_TEAM_NAME_BLACKLIST.get(league_api_str, set())
                
                if home_api_id in bl_ids or away_api_id in bl_ids:
                    self.stdout.write(self.style.WARNING(
                        f"  ⛔ BLACKLIST (ID): Pulando fixture {home_name} vs {away_name} "
                        f"(IDs: {home_api_id}/{away_api_id}) - Time não pertence à liga {db_league.name}"
                    ))
                    continue
                
                if home_name.lower() in bl_names or away_name.lower() in bl_names:
                    self.stdout.write(self.style.WARNING(
                        f"  ⛔ BLACKLIST (Nome): Pulando fixture {home_name} vs {away_name} "
                        f"- Time não pertence à liga {db_league.name}"
                    ))
                    continue
                
                # Normaliza os nomes antes da whitelist para garantir que aliases (ex: "Gremio Novorizontino") sejam convertidos para o nome oficial ("Novorizontino") antes da checagem
                from matches.utils import normalize_team_name
                home_name_norm = normalize_team_name(home_name)
                away_name_norm = normalize_team_name(away_name)
                
                # WHITELIST CHECK: Valida se os times pertencem à liga (segunda camada)
                if not is_team_valid_for_league(home_name_norm, db_league.name):
                    self.stdout.write(self.style.WARNING(
                        f"  🚫 WHITELIST: Rejeitado {home_name_norm} (original: {home_name}) - não pertence à {db_league.name}"
                    ))
                    continue
                if not is_team_valid_for_league(away_name_norm, db_league.name):
                    self.stdout.write(self.style.WARNING(
                        f"  🚫 WHITELIST: Rejeitado {away_name_norm} (original: {away_name}) - não pertence à {db_league.name}"
                    ))
                    continue
                # ============================================================
                
                # 1. Tenta achar o match pelo api_id do fixture
                match = Match.objects.filter(api_id=f_id).first()
                
                if not match:
                    # 2. Tenta parear pelos api_id de AMBOS os times (seguro)
                    match = Match.objects.filter(
                        league=db_league,
                        season=db_season,
                        home_team__api_id=home_api_id,
                        away_team__api_id=away_api_id
                    ).first()
                
                if not match:
                    # 3. Se não achou, CRIA o match novo com os times corretos
                    home_team = Team.objects.filter(api_id=home_api_id).first()
                    away_team = Team.objects.filter(api_id=away_api_id).first()
                    
                    # Se os times não existem no banco por api_id, verifica por nome e atualiza, senao cria
                    if not home_team:
                        home_team = Team.objects.filter(league=db_league, name__iexact=home_name).first()
                        if home_team:
                            home_team.api_id = home_api_id
                            home_team.save(update_fields=['api_id'])
                            self.stdout.write(f"  🔄 Time atualizado: {home_name} (API ID: {home_api_id})")
                        else:
                            home_team = Team.objects.create(name=home_name, api_id=home_api_id, league=db_league)
                            self.stdout.write(f"  🆕 Time criado: {home_name} (API ID: {home_api_id})")
                            
                    if not away_team:
                        away_team = Team.objects.filter(league=db_league, name__iexact=away_name).first()
                        if away_team:
                            away_team.api_id = away_api_id
                            away_team.save(update_fields=['api_id'])
                            self.stdout.write(f"  🔄 Time atualizado: {away_name} (API ID: {away_api_id})")
                        else:
                            away_team = Team.objects.create(name=away_name, api_id=away_api_id, league=db_league)
                            self.stdout.write(f"  🆕 Time criado: {away_name} (API ID: {away_api_id})")
                    
                    # Parseia a data do jogo
                    from django.utils.dateparse import parse_datetime
                    match_date = parse_datetime(f_date_str) if f_date_str else timezone.now()
                    
                    match = Match.objects.create(
                        league=db_league,
                        season=db_season,
                        home_team=home_team,
                        away_team=away_team,
                        date=match_date,
                        api_id=f_id,
                        round_name=round_name,
                        status='Scheduled'
                    )

                if match:
                    matched_count += 1
                    # Atualiza o status e placar basico sem gastar mais nada!
                    match.api_id = f_id
                    if f_status in ['FT', 'AET', 'PEN', 'FINISHED']:
                        match.status = 'Finished'
                        if home_goals is not None: match.home_score = home_goals
                        if away_goals is not None: match.away_score = away_goals
                    else:
                        match.status = 'Scheduled' if f_status in ['NS', 'TBD'] else f_status
                    
                    if round_name and not match.round_name:
                        match.round_name = round_name
                    match.save(update_fields=['api_id', 'status', 'home_score', 'away_score', 'round_name'])
            
            self.stdout.write(self.style.SUCCESS(f"✅ Pareados e atualizados placares base de {matched_count} jogos no banco!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro no passo 1: {e}"))
            return

        # 2. Buscar estatísticas (Escanteios, Chutes) apenas dos jogos finalizados
        # que ainda não têm esses dados preenchidos no nosso banco.
        self.stdout.write(self.style.SUCCESS(f"\n[2] Inspecionando jogos finalizados sem estatísticas..."))
        
        matches_needs_stats = Match.objects.filter(
            league=db_league,
            season=db_season,
            api_id__isnull=False,
            status__in=['Finished', 'FT', 'AET', 'PEN']
        ).filter(home_corners__isnull=True).order_by('-date')

        total_needs = matches_needs_stats.count()
        self.stdout.write(f"Encontrados {total_needs} jogos que precisam de escanteios.")
        
        if total_needs == 0:
            self.stdout.write(self.style.SUCCESS("Todos os jogos finalizados já possuem estatísticas! Nenhum crédito extra gasto."))
            return

        if stat_limit > 0:
            matches_needs_stats = matches_needs_stats[:stat_limit]
            self.stdout.write(f"Limiting to {stat_limit} chamadas por causa do parâmetro --limit.")

        stats_fetched = 0
        from matches.models import Goal
        for match in matches_needs_stats:
            api_id_str = str(match.api_id)
            if api_id_str.startswith('sofa_') or not ''.join(filter(str.isdigit, api_id_str)):
                self.stdout.write(f"  -> Ignorando jogo antigo do SofaScore ou ID invalido: {match.home_team.name} x {match.away_team.name} (API ID: {match.api_id})")
                continue
                
            # Extrai apenas os numeros caso tenha algum prefixo como API_
            clean_api_id = ''.join(filter(str.isdigit, api_id_str))
            
            self.stdout.write(f"  -> Buscando dados completos (Stats+Gols) de: {match.home_team.name} x {match.away_team.name} (API ID: {clean_api_id})")
            # Usa a rota /fixtures com id=... para trazer TODO O PACOTE (eventos, estatisticas, gols) por apenas 1 credito
            stat_params = {'id': clean_api_id}
            
            try:
                r_stats = api._make_request(f"{base_url}/fixtures", headers=headers, params=stat_params, timeout=10)
                api._increment_usage('api_football_1')
                time.sleep(0.5) # Throttle leve para n tomar rate limit rapido
                
                s_data_json = r_stats.json()
                if 'errors' in s_data_json and s_data_json['errors']:
                     self.stdout.write(self.style.ERROR(f"Erro ao buscar stats: {s_data_json['errors']}"))
                     break
                     
                stats_resp = s_data_json.get('response', [])
                if not stats_resp:
                    self.stdout.write("      ⚠ Sem dados disponíveis na API para este jogo.")
                    match.home_corners = 0
                    match.away_corners = 0
                    match.save(update_fields=['home_corners', 'away_corners'])
                    continue

                game_data = stats_resp[0]
                statistics = game_data.get('statistics', [])
                events = game_data.get('events', [])

                # Usar ESTRITAMENTE o ID da API-Football que vem no pacote para parear
                home_team_id_api = str(game_data['teams']['home']['id'])
                away_team_id_api = str(game_data['teams']['away']['id'])
                
                h_corners = 0
                a_corners = 0
                
                # --- 1. SALVAR ESCANTEIOS ---
                if statistics:
                    for team_stats in statistics:
                        t_id_api = str(team_stats['team']['id'])
                        corners_val = 0
                        for stat in team_stats.get('statistics', []):
                            if stat['type'] == 'Corner Kicks':
                                corners_val = stat['value'] if stat['value'] is not None else 0
                                break
                        
                        if t_id_api == home_team_id_api:
                            h_corners = corners_val
                        elif t_id_api == away_team_id_api:
                            a_corners = corners_val
                        else:
                            if statistics.index(team_stats) == 0:
                                h_corners = corners_val
                            else:
                                a_corners = corners_val
                                    
                match.home_corners = h_corners
                match.away_corners = a_corners
                match.save(update_fields=['home_corners', 'away_corners'])

                # --- 2. SALVAR GOLS ---
                # Limpa gols antigos para evitar duplicidade em caso de re-sincronização
                match.goals.all().delete()
                
                goals_saved = 0
                if events:
                    for ev in events:
                        if ev['type'] == 'Goal':
                            minute = ev['time']['elapsed']
                            if ev['time'].get('extra'):
                                minute += ev['time']['extra']
                                
                            player_name = ev['player']['name'] or "Unknown"
                            detail = ev.get('detail', '')
                            is_penalty = (detail == 'Penalty')
                            is_own_goal = (detail == 'Own Goal')
                            
                            t_id_api = str(ev['team']['id'])
                            
                            scoring_team = None
                            if t_id_api == home_team_id_api:
                                scoring_team = match.home_team
                            elif t_id_api == away_team_id_api:
                                scoring_team = match.away_team
                                
                            if scoring_team:
                                Goal.objects.create(
                                    match=match,
                                    team=scoring_team,
                                    player_name=player_name,
                                    minute=minute,
                                    is_penalty=is_penalty,
                                    is_own_goal=is_own_goal
                                )
                                goals_saved += 1

                stats_fetched += 1
                self.stdout.write(f"      ✓ Salvo: {h_corners}x{a_corners} Escanteios | {goals_saved} Gols registrados.")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"      ✗ Erro na requisição: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nFinalizado! {stats_fetched} jogos atualizados com pacote completo (Escanteios + Gols)."))
