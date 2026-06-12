import os
import sys
import time
import requests
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction

from matches.models import Match, Team

class Command(BaseCommand):
    help = "Daemon que busca dados ao vivo globais via API-Football (20s interval com Smart Sleep)"

    def handle(self, *args, **options):
        api_key = os.getenv("API_FOOTBALL_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("API_FOOTBALL_KEY não configurada no .env!"))
            return

        headers = {
            'x-apisports-key': api_key,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }

        self.stdout.write(self.style.SUCCESS("⚽ Iniciando o Live Score PRO (API-Football) - 20s Loop"))
        
        cycle = 1
        while True:
            # === SMART SLEEP LOGIC ===
            # Checa se temos jogos relevantes (Ao Vivo ou começando em 30 min)
            active_matches = Match.objects.filter(
                status__in=['Live', 'In Play', 'First Half', 'Second Half', 'Halftime', 'Extra Time', 'Penalty']
            )
            
            upcoming_matches = Match.objects.filter(
                status__in=['Scheduled', 'Not Started', 'Timed', 'Postponed'],
                date__lte=now() + timedelta(minutes=30),
                date__gte=now() - timedelta(hours=3) # Não buscar jogos muito velhos "presos"
            )
            
            if not active_matches.exists() and not upcoming_matches.exists():
                self.stdout.write(self.style.WARNING(f"[{datetime.now().strftime('%H:%M:%S')}] Ciclo #{cycle} - NENHUM JOGO ATIVO. Entrando em Smart Sleep por 10 minutos... zZz"))
                time.sleep(600) # 10 minutos
                cycle += 1
                continue
                
            self.stdout.write(self.style.SUCCESS(f"\n[{datetime.now().strftime('%H:%M:%S')}] Ciclo #{cycle} - Iniciando sincronização mundial..."))
            
            try:
                # Busca TODOS os jogos ao vivo no mundo (1 Request)
                url = "https://v3.football.api-sports.io/fixtures?live=all"
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    fixtures = data.get('response', [])
                    self.stdout.write(f"  → API-Football retornou {len(fixtures)} jogos ao vivo no mundo inteiro.")
                    
                    matches_updated = 0
                    
                    with transaction.atomic():
                        for fix in fixtures:
                            f_info = fix.get('fixture', {})
                            t_info = fix.get('teams', {})
                            g_info = fix.get('goals', {})
                            status_info = f_info.get('status', {})
                            
                            home_name = t_info.get('home', {}).get('name')
                            away_name = t_info.get('away', {}).get('name')
                            
                            # Tenta mapear o jogo pelo nome dos times (que já temos no banco)
                            try:
                                # A busca será por jogos de hoje +- 1 dia para evitar overlaps
                                db_match = Match.objects.get(
                                    home_team__name__icontains=home_name,
                                    away_team__name__icontains=away_name,
                                    date__gte=now() - timedelta(hours=5),
                                    date__lte=now() + timedelta(hours=5)
                                )
                                
                                # Atualiza status e gols
                                db_match.home_score = g_info.get('home') if g_info.get('home') is not None else db_match.home_score
                                db_match.away_score = g_info.get('away') if g_info.get('away') is not None else db_match.away_score
                                db_match.elapsed_time = status_info.get('elapsed')
                                
                                s_short = status_info.get('short')
                                if s_short in ['1H', '2H', 'ET', 'P', 'LIVE']:
                                    db_match.status = 'Live'
                                elif s_short == 'HT':
                                    db_match.status = 'Halftime'
                                elif s_short in ['FT', 'AET', 'PEN']:
                                    db_match.status = 'Finished'
                                elif s_short in ['CANC', 'PST', 'ABD']:
                                    db_match.status = 'Postponed'
                                
                                db_match.save()
                                matches_updated += 1
                                
                            except Match.DoesNotExist:
                                # O jogo existe na API mas o usuário não acompanha essa liga no banco de dados. Ignorar.
                                pass
                            except Match.MultipleObjectsReturned:
                                # Cuidado com times com nomes iguais em ligas diferentes, raro no mesmo dia.
                                pass
                                
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Sincronizou {matches_updated} jogos do nosso Radar com a API."))
                    
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ Erro da API: {response.status_code} - {response.text}"))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Erro de conexão/timeout: {e}"))
                
            self.stdout.write("Aguardando 20 segundos...\n" + "="*50)
            time.sleep(20)
            cycle += 1
