
from django.core.management.base import BaseCommand
from django.db import transaction
from matches.models import League, Team, Match, LeagueStanding, Goal, Player, TeamGoalTiming

class Command(BaseCommand):
    help = "Mescla ligas duplicadas (ex: 'Brasileirão' -> 'Brasileirao')"

    def handle(self, *args, **options):
        # 1. Deduplicação explícita (Renomear errado -> certo)
        MERGES = [
            ("Brasileirão", "Brasileirao", "Brasil"),
            ("Ligue 1", "Ligue 1", "França"), 
        ]
        
        self.stdout.write("--- Fase 1: Renomear e Mesclar nomes diferentes ---")
        for bad_name, good_name, country in MERGES:
            self._merge_league(bad_name, good_name, country)

        # 2. Deduplicação implícita (Mesclar ligas com MESMO NOME)
        # Isso corrige o caso onde existem 2 "Premier League" iguais
        self.stdout.write("--- Fase 2: Buscar duplicatas idênticas ---")
        self._merge_identical_duplicates()

    def _merge_identical_duplicates(self):
        # Encontra nomes de ligas que aparecem mais de uma vez
        from django.db.models import Count
        duplicates = League.objects.values('name', 'country').annotate(count=Count('id')).filter(count__gt=1)

        for entry in duplicates:
            name = entry['name']
            country = entry['country']
            self.stdout.write(self.style.WARNING(f"Encontrada duplicata idêntica: {name} ({country}) - {entry['count']} vezes"))
            
            # Pega todas as instâncias
            leagues = League.objects.filter(name=name, country=country).order_by('id')
            
            # A primeira (mais antiga) será a oficial
            primary_league = leagues.first()
            
            # As outras serão mescladas na primeira
            for duplicate in leagues[1:]:
                 self._merge_leagues_logic(duplicate, primary_league)

    def _merge_league(self, bad_name, good_name, country):
        try:
            # Tenta encontrar a liga "ruim"
            bad_leagues = League.objects.filter(name=bad_name)
            if country:
                 bad_leagues = bad_leagues.filter(country=country)
            
            if not bad_leagues.exists():
                return

            # Tenta encontrar a liga "boa"
            good_league = League.objects.filter(name=good_name)
            if country:
                good_league = good_league.filter(country=country)
            
            good_league = good_league.first()

            if not good_league:
                # Se a boa não existe, renomeia a ruim para a boa
                bad_league = bad_leagues.first()
                bad_league.name = good_name
                bad_league.save()
                self.stdout.write(self.style.SUCCESS(f"Renomeado '{bad_name}' para '{good_name}'"))
                # Se houver mais de uma ruim, as outras serão pegas na Fase 2
                return

            # Se ambas existem, mescla
            for bad_league in bad_leagues:
                if bad_league.id == good_league.id:
                    continue
                self._merge_leagues_logic(bad_league, good_league)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao mesclar ligas: {e}"))

    def _merge_leagues_logic(self, source_league, target_league):
        self.stdout.write(self.style.WARNING(f"Mesclando '{source_league.name}' (ID {source_league.id}) -> '{target_league.name}' (ID {target_league.id})"))
        
        with transaction.atomic():
            # Mover Times
            teams = Team.objects.filter(league=source_league)
            count_teams = teams.count()
            teams.update(league=target_league)
            
            # Mover Partidas
            matches = Match.objects.filter(league=source_league)
            count_matches = matches.count()
            matches.update(league=target_league)
            
            # Mover Standings
            standings = LeagueStanding.objects.filter(league=source_league)
            standings.update(league=target_league)

            # Deletar liga antiga
            source_league.delete()
        
        self.stdout.write(self.style.SUCCESS(f"  -> Movidos {count_teams} times e {count_matches} jogos."))
