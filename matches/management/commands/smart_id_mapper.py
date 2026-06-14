import os
import time
import difflib
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db.models import Q

from matches.models import League, Team, Match
from matches.api_manager import APIManager

class Command(BaseCommand):
    help = 'Mapeamento Econômico e Inteligente de IDs do SofaScore para API-Football'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando Mapeador Inteligente de IDs..."))
        api = APIManager()
        api_config = api.apis.get('api_football_1')
        if not api_config or not api_config.get('key'):
            self.stdout.write(self.style.ERROR("API_FOOTBALL_KEY não configurada!"))
            return
            
        headers = api._get_headers(api_config)
        credits_used = 0
        
        # 1. MAPEAMENTO DE LIGAS (Por País)
        self.stdout.write(self.style.WARNING("\n--- ETAPA 1: MAPEAMENTO DE LIGAS ---"))
        leagues_to_map = League.objects.filter(Q(api_id__isnull=True) | Q(api_id__startswith='sofa_'))
        countries = list(leagues_to_map.values_list('country', flat=True).distinct())
        
        self.stdout.write(f"Encontradas {leagues_to_map.count()} ligas precisando de mapeamento em {len(countries)} países.")
        
        for country in countries:
            if not country: continue
            
            self.stdout.write(f"Buscando ligas da API para o país: {country}")
            resp = api._make_request(f"{api_config['base_url']}/leagues", headers=headers, params={'country': country}, timeout=15)
            credits_used += 1
            time.sleep(1)
            
            if resp.status_code == 200:
                data = resp.json().get('response', [])
                api_leagues = [{'id': str(item['league']['id']), 'name': item['league']['name']} for item in data]
                
                db_leagues_country = leagues_to_map.filter(country=country)
                for db_l in db_leagues_country:
                    best_match = None
                    best_score = 0
                    for al in api_leagues:
                        score = difflib.SequenceMatcher(None, db_l.name.lower(), al['name'].lower()).ratio()
                        if score > best_score:
                            best_score = score
                            best_match = al
                    
                    if best_match and best_score > 0.60:
                        db_l.api_id = best_match['id']
                        db_l.save()
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Liga mapeada: {db_l.name} -> {best_match['id']}"))
            else:
                self.stdout.write(self.style.ERROR(f"  X Falha ao buscar ligas para {country}"))

        # 2. MAPEAMENTO DE TIMES E PARTIDAS (Por Liga)
        self.stdout.write(self.style.WARNING("\n--- ETAPA 2 e 3: MAPEAMENTO DE TIMES E PARTIDAS ---"))
        current_year = datetime.now().year
        
        # Só podemos mapear times/partidas de ligas que já tem um api_id puramente numérico (que não é do sofa_)
        valid_leagues = League.objects.exclude(api_id__isnull=True).exclude(api_id__startswith='sofa_')
        
        for league in valid_leagues:
            teams_to_map = league.teams.filter(Q(api_id__isnull=True) | Q(api_id__startswith='sofa_'))
            matches_to_map = Match.objects.filter(
                Q(home_team__league=league) | Q(away_team__league=league),
                date__gte=now() - timedelta(days=15),
                date__lte=now() + timedelta(days=60)
            ).filter(Q(api_id__isnull=True) | Q(api_id__startswith='sofa_')).distinct()
            
            if not teams_to_map.exists() and not matches_to_map.exists():
                continue
                
            self.stdout.write(f"\nLiga: {league.name} (API ID: {league.api_id})")
            
            # --- MAPEAMENTO DE TIMES ---
            if teams_to_map.exists():
                self.stdout.write(f"  -> Mapeando {teams_to_map.count()} times...")
                resp_t = api._make_request(f"{api_config['base_url']}/teams", headers=headers, params={'league': league.api_id, 'season': current_year}, timeout=15)
                credits_used += 1
                time.sleep(1)
                
                if resp_t.status_code == 200:
                    api_teams = resp_t.json().get('response', [])
                    api_t_list = [{'id': str(t['team']['id']), 'name': t['team']['name']} for t in api_teams]
                    
                    for db_t in teams_to_map:
                        best_t_match = None
                        best_t_score = 0
                        for at in api_t_list:
                            score = difflib.SequenceMatcher(None, db_t.name.lower(), at['name'].lower()).ratio()
                            if score > best_t_score:
                                best_t_score = score
                                best_t_match = at
                        
                        if best_t_match and best_t_score > 0.60:
                            db_t.api_id = best_t_match['id']
                            db_t.save()
                            self.stdout.write(self.style.SUCCESS(f"    ✓ Time mapeado: {db_t.name} -> {best_t_match['id']}"))

            # --- MAPEAMENTO DE PARTIDAS ---
            if matches_to_map.exists():
                self.stdout.write(f"  -> Mapeando {matches_to_map.count()} partidas recentes/futuras...")
                resp_m = api._make_request(f"{api_config['base_url']}/fixtures", headers=headers, params={'league': league.api_id, 'season': current_year}, timeout=15)
                credits_used += 1
                time.sleep(1)
                
                if resp_m.status_code == 200:
                    api_fixtures = resp_m.json().get('response', [])
                    
                    for db_m in matches_to_map:
                        db_h_name = db_m.home_team.name.lower().replace('-', ' ').strip()
                        db_a_name = db_m.away_team.name.lower().replace('-', ' ').strip()
                        
                        found = False
                        for f in api_fixtures:
                            api_h_name = f['teams']['home']['name'].lower().replace('-', ' ').strip()
                            api_a_name = f['teams']['away']['name'].lower().replace('-', ' ').strip()
                            
                            match_h = (db_h_name in api_h_name) or (api_h_name in db_h_name)
                            match_a = (db_a_name in api_a_name) or (api_a_name in db_a_name)
                            
                            if match_h and match_a:
                                db_m.api_id = str(f['fixture']['id'])
                                db_m.save()
                                self.stdout.write(self.style.SUCCESS(f"    ✓ Partida mapeada: {db_m.home_team.name} x {db_m.away_team.name} -> {f['fixture']['id']}"))
                                found = True
                                break
                        
                        if not found:
                            self.stdout.write(self.style.WARNING(f"    X Partida não encontrada na API: {db_m.home_team.name} x {db_m.away_team.name}"))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 MAPEAMENTO CONCLUÍDO!"))
        self.stdout.write(self.style.SUCCESS(f"💰 Créditos da API consumidos nesta rodada: {credits_used}"))
