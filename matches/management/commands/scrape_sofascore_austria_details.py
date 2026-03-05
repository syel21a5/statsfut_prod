import time
import json
from curl_cffi import requests
from django.core.management.base import BaseCommand
from matches.models import League, Match, Goal
from django.db import transaction

class Command(BaseCommand):
    help = "Busca estatísticas detalhadas (escanteios, cartões) e incidentes (gols, minutos) para as partidas da Áustria via SofaScore"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session(impersonate="chrome110")
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Origin": "https://www.sofascore.com",
            "Referer": "https://www.sofascore.com/"
        })

    def fetch_api(self, url):
        try:
            time.sleep(1.5)  # Respect rate limits
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None # Normal, match might not have stats
            else:
                self.stdout.write(self.style.ERROR(f"Erro na API {url}: Status {response.status_code}"))
                return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Exceção ao acessar {url}: {e}"))
            return None

    def handle(self, *args, **kwargs):
        league = League.objects.filter(country='Austria').first()
        if not league:
            self.stdout.write(self.style.ERROR("Liga da Áustria não encontrada. Execute 'scrape_sofascore_austria' primeiro."))
            return

        # Busca apenas as partidas Concluídas que vieram do SofaScore
        matches = Match.objects.filter(
            league=league, 
            status__in=['Finished', 'FT', 'AET', 'PEN'],
            api_id__startswith='sofa_'
        )

        self.stdout.write(self.style.SUCCESS(f"Iniciando busca detalhada para {matches.count()} partidas da Áustria..."))

        stats_updated = 0
        incidents_updated = 0

        for match in matches:
            sofa_id = match.api_id.replace('sofa_', '')
            self.stdout.write(f"  > Processando Partida {match.id} (Sofa ID: {sofa_id}) | {match.home_team} x {match.away_team}")
            
            # --- 1. ESTATÍSTICAS ---
            stats_url = f"https://api.sofascore.com/api/v1/event/{sofa_id}/statistics"
            stats_data = self.fetch_api(stats_url)
            
            stats_found = False
            if stats_data and 'statistics' in stats_data:
                stats_list = stats_data['statistics']
                if stats_list:
                    all_group = stats_list[0].get('groups', []) # Get "ALL" period
                    
                    for group in all_group:
                        for stat in group.get('statisticsItems', []):
                            name = stat.get('name')
                            h_val = stat.get('home')
                            a_val = stat.get('away')
                            
                            # Clean up string values like "12%" to integer if needed, but SofaScore usually provides ints
                            try:
                                h_val = int(str(h_val).replace('%', '').strip()) if h_val is not None else None
                                a_val = int(str(a_val).replace('%', '').strip()) if a_val is not None else None
                            except ValueError:
                                pass # Keep as is if conversion fails

                            if name == 'Corner kicks':
                                match.home_corners = h_val
                                match.away_corners = a_val
                            elif name == 'Yellow cards':
                                match.home_yellow = h_val
                                match.away_yellow = a_val
                            elif name == 'Red cards':
                                match.home_red = h_val
                                match.away_red = a_val
                            elif name == 'Shots on target':
                                match.home_shots_on_target = h_val
                                match.away_shots_on_target = a_val
                            elif name == 'Total shots':
                                match.home_shots = h_val
                                match.away_shots = a_val
                            elif name == 'Fouls':
                                match.home_fouls = h_val
                                match.away_fouls = a_val
                    
                    match.save()
                    stats_found = True
                    stats_updated += 1
            
            if not stats_found:
                 self.stdout.write(self.style.WARNING("    - Sem estatísticas disponíveis."))

            # --- 2. INCIDENTES (GOLS) ---
            incidents_url = f"https://api.sofascore.com/api/v1/event/{sofa_id}/incidents"
            inc_data = self.fetch_api(incidents_url)
            
            if inc_data and 'incidents' in inc_data:
                gols_list = [i for i in inc_data['incidents'] if i.get('incidentClass') == 'goal']
                
                if gols_list:
                    # Clear existing goals for this match to avoid duplicates if run multiple times
                    Goal.objects.filter(match=match).delete()
                    
                    with transaction.atomic():
                        for gol in gols_list:
                            minuto = gol.get('time')
                            jogador = gol.get('player', {}).get('name', 'Origin Desconhecida')
                            is_home = gol.get('isHome')
                            
                            # Determine team
                            team = match.home_team if is_home else match.away_team
                            
                            # Create DB Record
                            Goal.objects.create(
                                match=match,
                                team=team,
                                player_name=jogador,
                                minute=minuto,
                                is_own_goal=(gol.get('incidentType') == 'ownGoal'),
                                is_penalty=(gol.get('incidentType') == 'penalty')
                            )
                    incidents_updated += 1
                    self.stdout.write(self.style.SUCCESS(f"    - +{len(gols_list)} gols registrados."))
                else:
                    self.stdout.write("    - Nenhum incidente de gol.")
            
        self.stdout.write(self.style.SUCCESS(f"Finalizado! {stats_updated} jogos receberam estatísticas avançadas e {incidents_updated} receberam dados granulares de gols."))
