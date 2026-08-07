import os
import django
from datetime import datetime, timedelta

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match

def seed():
    print("Semeando dados...")
    
    # Criar Ligas
    premier, _ = League.objects.get_or_create(name="Premier League", country="Inglaterra")
    brasileirao, _ = League.objects.get_or_create(name="Brasileirão", country="Brasil")
    
    # Criar Times Premier League
    arsenal, _ = Team.objects.get_or_create(name="Arsenal", league=premier)
    city, _ = Team.objects.get_or_create(name="Man City", league=premier)
    liverpool, _ = Team.objects.get_or_create(name="Liverpool", league=premier)
    
    # Criar Times Brasileirão
    palmeiras, _ = Team.objects.get_or_create(name="Palmeiras", league=brasileirao)
    flamengo, _ = Team.objects.get_or_create(name="Flamengo", league=brasileirao)
    botafogo, _ = Team.objects.get_or_create(name="Botafogo", league=brasileirao)
    
    # Criar Jogos
    now = datetime.now()
    
    # Jogo 1
    Match.objects.get_or_create(
        league=premier,
        home_team=arsenal,
        away_team=city,
        date=now + timedelta(hours=2),
        home_score=None,
        away_score=None
    )
    
    # Jogo 2
    Match.objects.get_or_create(
        league=brasileirao,
        home_team=palmeiras,
        away_team=flamengo,
        date=now + timedelta(hours=5),
        home_score=None,
        away_score=None
    )
    
    # Jogo Passado (para estatística)
    Match.objects.get_or_create(
        league=premier,
        home_team=liverpool,
        away_team=arsenal,
        date=now - timedelta(days=2),
        home_score=3,
        away_score=1
    )

    print("Dados inseridos com sucesso!")

if __name__ == "__main__":
    seed()
