from django.core.management.base import BaseCommand
from matches.models import Team, Player

class Command(BaseCommand):
    help = 'Seeds Arsenal players with age and details'

    def handle(self, *args, **kwargs):
        # Find Arsenal
        teams = Team.objects.filter(name__icontains='Arsenal')
        if not teams.exists():
            self.stdout.write(self.style.ERROR('Arsenal team not found'))
            return
            
        # Prefer PL Arsenal if multiple
        arsenal = teams.filter(league__name__icontains='Premier').first() or teams.first()
        
        self.stdout.write(f"Seeding players for: {arsenal.name} ({arsenal.league.name})")

        # Player Data (Name, Age, Nationality)
        # Based on user's screenshot/request 2025/26 context
        # Ages are approx for that future season context
        players_data = [
            {"name": "Leandro Trossard", "age": 31, "nat": "Belgium"},
            {"name": "Viktor Gyökeres", "age": 27, "nat": "Sweden"}, # From screenshot
            {"name": "Eberechi Eze", "age": 27, "nat": "England"},   # From screenshot
            {"name": "Declan Rice", "age": 26, "nat": "England"},
            {"name": "Bukayo Saka", "age": 24, "nat": "England"},
            {"name": "Gabriel Magalhães", "age": 28, "nat": "Brazil"},
            {"name": "Mikel Merino", "age": 29, "nat": "Spain"},
            {"name": "Martín Zubimendi", "age": 26, "nat": "Spain"}, # From screenshot
            {"name": "Jurrien Timber", "age": 24, "nat": "Netherlands"},
            {"name": "Gabriel Jesus", "age": 28, "nat": "Brazil"},
            {"name": "Martin Ødegaard", "age": 27, "nat": "Norway"},
            {"name": "Gabriel Martinelli", "age": 24, "nat": "Brazil"},
            {"name": "Riccardo Calafiori", "age": 23, "nat": "Italy"},
            {"name": "Kai Havertz", "age": 26, "nat": "Germany"},
            {"name": "William Saliba", "age": 24, "nat": "France"},
            {"name": "Ben White", "age": 28, "nat": "England"},
            {"name": "David Raya", "age": 30, "nat": "Spain"},
            {"name": "Thomas Partey", "age": 32, "nat": "Ghana"},
        ]

        created_count = 0
        updated_count = 0

        for p_data in players_data:
            player, created = Player.objects.update_or_create(
                team=arsenal,
                name=p_data['name'],
                defaults={
                    'age': p_data['age'],
                    'nationality': p_data['nat']
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Finished: Created {created_count}, Updated {updated_count} players."))
