import json
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import Match, League
from matches.utils_odds_api import resolve_team
from matches.services.betano_scraper import setup_proxy_session, fetch_betano_upcoming, extract_odds_from_betano_data

class Command(BaseCommand):
    help = 'Busca e atualiza as odds dos próximos jogos via Betano/Altenar usando Proxy Residencial'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("⚠️ AVISO: Este script (Betano) está OBSOLETO. Use 'python manage.py update_pro_odds' que utiliza a API-Football PRO."))
        self.stdout.write("Iniciando scraper da Betano via Proxy Residencial...")
        
        session = setup_proxy_session()
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
            fields_to_update = []
            
            mapping = {
                'home_win': 'home_team_win_odds',
                'draw': 'draw_odds',
                'away_win': 'away_team_win_odds',
            }
            
            for field, odd_value in markets.items():
                if odd_value > 0:
                    model_field = mapping.get(field, f"{field}_odds")
                    if hasattr(match, model_field):
                        # Evitar saves desnecessários se a odd não mudou
                        if getattr(match, model_field) != odd_value:
                            setattr(match, model_field, odd_value)
                            if model_field not in fields_to_update:
                                fields_to_update.append(model_field)
                                updated = True
                
            if updated and fields_to_update:
                match.save(update_fields=fields_to_update)
                updates += 1
                self.stdout.write(f"✅ Odds atualizadas: {match.home_team.name} x {match.away_team.name}")

        if updates > 0:
            from django.core.cache import cache
            cache.delete('premium_dashboard_context_v1')
            self.stdout.write("🧹 Cache do Dashboard Premium limpo com sucesso!")

        self.stdout.write(self.style.SUCCESS(f"Processo concluído! {updates} partidas tiveram suas odds atualizadas."))
