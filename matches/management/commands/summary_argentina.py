from django.core.management.base import BaseCommand
from matches.models import League, Match
from collections import defaultdict

class Command(BaseCommand):
    help = "Resumo por ano da Argentina"

    def handle(self, *args, **kwargs):
        leagues = League.objects.filter(country="Argentina").order_by("name")
        if not leagues.exists():
            self.stdout.write("Nenhuma liga da Argentina encontrada")
            return
        for league in leagues:
            per_year = defaultdict(int)
            qs = Match.objects.filter(league=league).values_list("date", flat=True)
            for d in qs:
                if d:
                    per_year[d.year] += 1
            total = sum(per_year.values())
            self.stdout.write(f"Liga: {league.name} | Total: {total}")
            for y in sorted(per_year.keys()):
                self.stdout.write(f"{y}: {per_year[y]}")
            self.stdout.write("---")
