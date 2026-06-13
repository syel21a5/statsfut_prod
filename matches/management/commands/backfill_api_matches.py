import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import League, Match, Season, Team
from matches.api_manager import APIManager

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
                
                # Tenta achar o match pelo api_id
                match = Match.objects.filter(api_id=f_id).first()
                if not match:
                    # Se não tem api_id, tenta parear pelo time da casa e da fora
                    home_name = fix['teams']['home']['name']
                    away_name = fix['teams']['away']['name']
                    match = Match.objects.filter(
                        league=db_league,
                        season=db_season,
                        home_team__api_id=str(fix['teams']['home']['id'])
                    ).first()
                    # Fallback por nome caso os times nao tenham api_id
                    if not match:
                        match = Match.objects.filter(
                            league=db_league,
                            season=db_season,
                            home_team__name__icontains=home_name[:5],
                            away_team__name__icontains=away_name[:5]
                        ).first()

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
                    match.save(update_fields=['api_id', 'status', 'home_score', 'away_score'])
            
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
            self.stdout.write(f"  -> Buscando dados completos (Stats+Gols) de: {match.home_team.name} x {match.away_team.name} (API ID: {match.api_id})")
            # Usa a rota /fixtures com id=... para trazer TODO O PACOTE (eventos, estatisticas, gols) por apenas 1 credito
            stat_params = {'id': match.api_id}
            
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
