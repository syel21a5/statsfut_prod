import json
import os
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
from matches.models import Match, Team, League, Season

class Command(BaseCommand):
    help = "Diagnostica por que as partidas do deep scrape não estão sendo encontradas no servidor"

    def handle(self, *args, **options):
        json_file = 'deep_scrape_exports/dados_deep_scrape.json'
        
        if not os.path.exists(json_file):
            self.stdout.write(self.style.ERROR(f"Arquivo {json_file} não encontrado!"))
            return

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.stdout.write(f"Analisando {len(data)} partidas do deep scrape...")

        # 1. Verificar Liga
        leagues_in_json = set((item.get('league_name'), item.get('league_country')) for item in data)
        self.stdout.write("\nLigas no JSON:")
        for name, country in leagues_in_json:
            db_leagues = League.objects.filter(name__iexact=name, country__iexact=country)
            self.stdout.write(f" - {country} - {name}: Encontradas no banco do servidor: {[l.id for l in db_leagues]}")

        # 2. Identificar partidas não encontradas
        missing_count = 0
        missing_details = []

        for item in data:
            api_id = item['api_id']
            if not api_id:
                continue

            match = Match.objects.filter(api_id=api_id).first()
            if not match:
                # Tenta fallback por nome + data para ver se encontraria com a lógica atual
                home_team_name = item.get('home_team', '')
                away_team_name = item.get('away_team', '')
                match_date = item.get('date')
                league_name = item.get('league_name')
                league_country = item.get('league_country')

                found_by_fallback = False
                candidates_found = []
                
                if match_date and home_team_name and away_team_name:
                    try:
                        dt = parse_datetime(match_date.replace('Z', '+00:00')) if 'Z' in str(match_date) or '+' in str(match_date) else datetime.fromisoformat(str(match_date))
                        date_only = dt.date()
                    except:
                        dt = None
                        date_only = None

                    if date_only:
                        day_start = datetime.combine(date_only, datetime.min.time()) - timedelta(hours=14)
                        day_end = datetime.combine(date_only, datetime.max.time()) + timedelta(hours=14)
                        
                        candidates = Match.objects.filter(date__range=(day_start, day_end))
                        
                        # Filtragem de liga
                        if league_name and league_country:
                            league = League.objects.filter(name__iexact=league_name, country__iexact=league_country).first()
                            if league:
                                candidates = candidates.filter(league=league)
                            else:
                                candidates = candidates.filter(league__name__icontains=league_name)
                        
                        for candidate in candidates:
                            candidates_found.append(f"{candidate.home_team.name if candidate.home_team else '?'} x {candidate.away_team.name if candidate.away_team else '?'} (api_id={candidate.api_id}, id={candidate.id}, date={candidate.date})")
                            h_name = candidate.home_team.name.lower() if candidate.home_team else ''
                            a_name = candidate.away_team.name.lower() if candidate.away_team else ''
                            h_search = home_team_name.lower()
                            a_search = away_team_name.lower()
                            
                            h_match = h_search in h_name or h_name in h_search or h_search.split()[0] in h_name.split() if h_search.split() else False
                            a_match = a_search in a_name or a_name in a_search or a_search.split()[0] in a_name.split() if a_search.split() else False
                            
                            if h_match and a_match:
                                found_by_fallback = True
                                break

                if not found_by_fallback:
                    missing_count += 1
                    missing_details.append({
                        'api_id': api_id,
                        'home': home_team_name,
                        'away': away_team_name,
                        'date': match_date,
                        'candidates': candidates_found
                    })

        self.stdout.write(self.style.WARNING(f"\nTotal de partidas não encontradas (erros): {missing_count}"))
        
        if missing_details:
            self.stdout.write("\nExemplos de partidas não encontradas e candidatos no mesmo dia:")
            for i, det in enumerate(missing_details[:10]):
                self.stdout.write(f"\n[{i+1}] JSON: {det['home']} x {det['away']} (api_id={det['api_id']}, date={det['date']})")
                if det['candidates']:
                    self.stdout.write("    Candidatos no banco para o mesmo dia:")
                    for c in det['candidates']:
                        self.stdout.write(f"      - {c}")
                else:
                    self.stdout.write("    Nenhum candidato encontrado no banco para este dia.")

                # Verifica se os times existem no banco
                h_exists = Team.objects.filter(name__iexact=det['home']).exists()
                a_exists = Team.objects.filter(name__iexact=det['away']).exists()
                self.stdout.write(f"    Times no banco? Casa ({det['home']}): {'SIM' if h_exists else 'NÃO'} | Fora ({det['away']}): {'SIM' if a_exists else 'NÃO'}")
