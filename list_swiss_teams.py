import os
import sys
import django
from django.utils.text import slugify

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team

try:
    with open('teams_suica_output.txt', 'w', encoding='utf-8') as f:
        teams = Team.objects.filter(league__country='Suica')
        f.write(f"Total de times encontrados: {teams.count()}\n")
        for t in teams:
            f.write(f"{t.name} -> {slugify(t.name)}\n")
    print("Arquivo teams_suica_output.txt criado com sucesso!")
except Exception as e:
    print(f"Erro ao criar arquivo: {e}")
