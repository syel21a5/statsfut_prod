from matches.models import Season
from django.db.models import Count

dupes = Season.objects.values('year').annotate(count=Count('id')).filter(count__gt=1)

for d in dupes:
    year = d['year']
    print(f"Fixing duplicate seasons for year {year}...")
    seasons = list(Season.objects.filter(year=year).order_by('id'))
    
    # Keep the first one (usually oldest ID)
    primary = seasons[0]
    others = seasons[1:]
    
    for s in others:
        print(f"  Merging Season ID {s.id} into {primary.id}...")
        # Move related matches
        s.matches.update(season=primary)
        # Move related standings
        s.standings.update(season=primary)
        # Delete duplicate
        s.delete()
        print(f"  Deleted Season ID {s.id}")

print("Season cleanup done.")
