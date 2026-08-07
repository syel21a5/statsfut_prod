import os
import django
import sys

# Setup Django environment (use current working directory to avoid drive mismatches)
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League

# Lista de ligas desejadas (name, country) exatamente como solicitado
LEAGUES_TO_SEED = [
    ('Premier League', 'Inglaterra'),
    ('Brasileirão', 'Brasil'),
    ('Premier League', 'Inglaterra'),
    ('La Liga', 'Espanha'),
    ('Brasileirão', 'Brasil'),
    ('Serie A', 'Italia'),
    ('Bundesliga', 'Alemanha'),
    ('Ligue 1', 'Franca'),
    ('Eredivisie', 'Holanda'),
    ('Pro League', 'Belgica'),
    ('Premier League', 'Russia'),
    ('Premier League', 'Ucrania'),
    ('Allsvenskan', 'Suecia'),
    ('Eliteserien', 'Noruega'),
    ('Superliga', 'Dinamarca'),
    ('Veikkausliiga', 'Finlandia'),
    ('Super League', 'Grecia'),
    ('J1 League', 'Japao'),
    ('K League 1', 'Coreia do Sul'),
    ('Super League', 'China'),
    ('A League', 'Australia'),
    ('Liga Profesional', 'Argentina'),
    ('Bundesliga', 'Austria'),
    ('Super League', 'Suica'),
    ('First League', 'Republica Tcheca'),
    ('Ekstraklasa', 'Polonia'),
    ('Premiership', 'Escocia'),
    ('Cymru Premier', 'Gales'),
    ('Premier Division', 'Irlanda'),
    ('Primera A', 'Colombia'),
    ('Primera Division', 'Chile'),
    ('Liga MX', 'Mexico'),
    ('Primera Division', 'Uruguai'),
    ('Primeira Liga', 'Portugal'),
    ('MLS', 'Estados Unidos'),
    ('Super Lig', 'Turquia'),
]

print("--- Seeding ligas na tabela 'matches_league' (local) ---")
created = 0
skipped = 0

for name, country in LEAGUES_TO_SEED:
    exists = League.objects.filter(name__iexact=name, country__iexact=country).exists()
    if not exists:
        League.objects.create(name=name, country=country)
        print(f"Created: {name} ({country})")
        created += 1
    else:
        print(f"Exists:  {name} ({country})")
        skipped += 1

print(f"\n--- Done. Created: {created}, Existing: {skipped}. ---")
