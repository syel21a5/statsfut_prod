from matches.models import Team
print('Western Uniteds:', list(Team.objects.filter(name__icontains='Western United').values('id', 'name')))
