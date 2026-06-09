import json
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import Match, League
from matches.utils_odds_api import resolve_team
from matches.services.betano_scraper import setup_tor_session, fetch_betano_upcoming, extract_odds_from_betano_data

class Command(BaseCommand):
    help = 'Busca e atualiza as odds dos próximos jogos via Betano/Altenar usando a rede Tor'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando scraper da Betano via Tor...")
        
        session = setup_tor_session()
        raw_data = fetch_betano_upcoming(session)
        
        if not raw_data:
            self.stderr.write("Falha ao baixar dados da Betano.")
            return
            
        events = extract_odds_from_betano_data(raw_data)
        self.stdout.write(f"Sucesso! {len(events)} eventos extraídos da Betano.")
        
        # Mapeamento para acelerar buscas (ignoramos ligas não cadastradas)
        updates = 0
        now = timezone.now()
        start_window = now - timedelta(hours=12)
        end_window = now + timedelta(days=7)
        
        for ev in events:
            home_name = ev['home_team']
            away_name = ev['away_team']
            markets = ev['markets']
            
            # Aqui fazemos um match tentativo no banco
            # Como a Betano não fornece o ID da nossa liga, vamos procurar por times
            # que tenham jogo marcado para as próximas 48h.
            # O ideal é usar o utils_odds_api.resolve_team iterando nas ligas ativas,
            # mas uma busca direta no Match pode ser mais eficiente:
            
            # Buscando de forma abrangente com icontains
            matches = Match.objects.filter(
                date__range=(start_window, end_window),
                home_team__name__icontains=home_name[:5], # Heurística simples
                away_team__name__icontains=away_name[:5]
            )
            
            match = matches.first()
            if not match:
                continue
                
            # Se achou, atualiza as odds
            updated = False
            
            if 'home_win' in markets and markets['home_win'] > 0:
                match.home_team_win_odds = markets['home_win']
                updated = True
            if 'draw' in markets and markets['draw'] > 0:
                match.draw_odds = markets['draw']
                updated = True
            if 'away_win' in markets and markets['away_win'] > 0:
                match.away_team_win_odds = markets['away_win']
                updated = True
                
            if 'btts_yes' in markets and markets['btts_yes'] > 0:
                match.btts_yes_odds = markets['btts_yes']
                updated = True
            if 'btts_no' in markets and markets['btts_no'] > 0:
                match.btts_no_odds = markets['btts_no']
                updated = True
                
            if 'over_25' in markets and markets['over_25'] > 0:
                match.over_25_odds = markets['over_25']
                updated = True
            if 'under_25' in markets and markets['under_25'] > 0:
                match.under_25_odds = markets['under_25']
                updated = True
                
            if updated:
                match.save(update_fields=[
                    'home_team_win_odds', 'draw_odds', 'away_team_win_odds',
                    'btts_yes_odds', 'btts_no_odds', 'over_25_odds', 'under_25_odds'
                ])
                updates += 1
                self.stdout.write(f"✅ Odds atualizadas: {match.home_team.name} x {match.away_team.name}")

        self.stdout.write(self.style.SUCCESS(f"Processo concluído! {updates} partidas tiveram suas odds atualizadas."))
