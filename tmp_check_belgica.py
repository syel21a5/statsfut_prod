from matches.models import Match, League
from django.db.models import Count, Avg, Sum
liga = League.objects.get(id=10)
print("Liga: " + liga.name)
tots = Match.objects.filter(league=liga).values("season").annotate(total=Count("id")).order_by("season")
for t in tots:
    print("  Temporada " + str(t["season"]) + ": " + str(t["total"]) + " partidas")
print("Total: " + str(Match.objects.filter(league=liga).count()))

