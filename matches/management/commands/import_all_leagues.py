import os
import json
from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import League

class Command(BaseCommand):
    help = "Importa automaticamente todos os payloads JSON encontrados na raiz para suas respectivas ligas."

    def handle(self, *args, **options):
        # Mapeamento de arquivos para nomes de ligas/países conhecidos
        mapping = {
            'payload_argentina.json': {'name': 'Liga Profesional', 'country': 'Argentina'},
            'payload_brasil.json': {'name': 'Brasileirão', 'country': 'Brasil'},
            'payload_austria.json': {'name': 'Bundesliga', 'country': 'Austria'},
            'payload_suica.json': {'name': 'Super League', 'country': 'Switzerland'},
            'payload_alemanha.json': {'name': 'Bundesliga', 'country': 'Germany'},
            'payload_franca.json': {'name': 'Ligue 1', 'country': 'France'},
            'payload_belgica.json': {'name': 'Pro League', 'country': 'Belgium'},
            'payload_australia.json': {'name': 'A-League Men', 'country': 'Australia'},
            'payload_dinamarca.json': {'name': 'Superliga', 'country': 'Dinamarca'},
            'payload_inglaterra.json': {'name': 'Premier League', 'country': 'Inglaterra'},
            'payload_espanha.json': {'name': 'La Liga', 'country': 'Espanha'},
            'payload_finlandia.json': {'name': 'Veikkausliiga', 'country': 'Finlandia'},
            'payload_grecia.json': {'name': 'Super League', 'country': 'Grecia'},
            'payload_holanda.json': {'name': 'Eredivisie', 'country': 'Holanda'},
            'payload_italia.json': {'name': 'Serie A', 'country': 'Italia'},
        }

        self.stdout.write("🔍 Iniciando busca de payloads na raiz...")

        for filename, info in mapping.items():
            if os.path.exists(filename):
                self.stdout.write(self.style.SUCCESS(f"found: {filename}"))
                try:
                    league = League.objects.filter(name__iexact=info['name'], country__iexact=info['country']).first()
                    if not league:
                        # Tenta busca mais flexível
                        league = League.objects.filter(name__icontains=info['name'], country__icontains=info['country']).first()
                    
                    if league:
                        self.stdout.write(f"-> Importando {filename} para a liga {league.name} (ID: {league.id})")
                        call_command('import_sofascore_payload', file=filename, league_id=league.id)
                    else:
                        self.stdout.write(self.style.WARNING(f"-> Ignorado: Liga {info['name']} ({info['country']}) nao encontrada no banco."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"-> Erro ao importar {filename}: {e}"))
            else:
                self.stdout.write(self.style.NOTICE(f"skip: {filename} (arquivo nao encontrado)"))

        self.stdout.write(self.style.SUCCESS("✅ Processo de importação em massa concluído!"))
