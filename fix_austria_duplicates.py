import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match, LeagueStanding
from django.db.models import Q

def merge_teams(league, wrong_name, correct_name):
    try:
        correct_team = Team.objects.get(league=league, name=correct_name)
    except Team.DoesNotExist:
        print(f"Time CORRETO '{correct_name}' não existe. Tentando renomear o errado se existir...")
        try:
            wrong_team = Team.objects.get(league=league, name=wrong_name)
            wrong_team.name = correct_name
            wrong_team.save()
            print(f"Renomeado '{wrong_name}' para '{correct_name}'.")
            return
        except Team.DoesNotExist:
            print(f"Nem '{wrong_name}' nem '{correct_name}' existem. Pulando.")
            return

    try:
        wrong_team = Team.objects.get(league=league, name=wrong_name)
    except Team.DoesNotExist:
        print(f"Time ERRADO '{wrong_name}' não existe. Nada a fazer.")
        return

    print(f"\nFundindo '{wrong_name}' -> '{correct_name}'...")

    # 1. Update Matches (Home)
    updated_home = Match.objects.filter(home_team=wrong_team).update(home_team=correct_team)
    print(f"- Atualizados {updated_home} jogos como mandante.")

    # 2. Update Matches (Away)
    updated_away = Match.objects.filter(away_team=wrong_team).update(away_team=correct_team)
    print(f"- Atualizados {updated_away} jogos como visitante.")

    # 3. Delete Wrong Team Standings
    deleted_standings, _ = LeagueStanding.objects.filter(team=wrong_team).delete()
    print(f"- Deletadas {deleted_standings} entradas na tabela.")

    # 4. Delete Wrong Team
    wrong_team.delete()
    print(f"- Time '{wrong_name}' deletado com sucesso.")

def run():
    league = League.objects.filter(name__icontains="Bundesliga", country="Austria").first()
    if not league:
        print("Liga da Áustria não encontrada.")
        return

    print(f"Processando liga: {league.name} ({league.country})")
    
    # Check all teams
    teams = Team.objects.filter(league=league)
    print("\nTimes existentes no banco:")
    for t in teams:
        print(f"- {t.name}")

    # Mapeamento (Errado -> Certo) baseado nos prints
    merges = [
        ("RB Salzburg", "Salzburg"),
        ("Red Bull Salzburg", "Salzburg"),
        ("FC Red Bull Salzburg", "Salzburg"),
        
        ("SK Rapid", "Rapid Wien"),
        ("Rapid Vienna", "Rapid Wien"),
        
        ("Blau-Weiss Linz", "BW Linz"),
        ("FC Blau-Weiß Linz", "BW Linz"),
        
        ("LASK", "LASK Linz"),
        
        ("Austria Vienna", "Austria Wien"),
        
        ("Rheindorf Altach", "Altach"),
        ("SCR Altach", "Altach"),

        ("WSG Tirol", "Tirol"),
        ("TSV Hartberg", "Hartberg"),
        ("SV Ried", "Ried"),
        ("Wolfsberg", "Wolfsberger AC"),
        ("Grazer AK 1902", "Grazer AK"),
        ("GAK", "Grazer AK"),
    ]

    for wrong, correct in merges:
        merge_teams(league, wrong, correct)

    print("\nConcluído. Agora rode recalculate_standings.")

if __name__ == "__main__":
    run()
