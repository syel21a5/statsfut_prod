from matches.models import Team, Match, League

try:
    # 1. Buscar o time
    wu = Team.objects.get(name__icontains="Western United", league__name="A League")
    print(f"Time encontrado: {wu.name} (ID: {wu.id})")
    
    # 2. Buscar partidas (Home/Away)
    home_games = Match.objects.filter(home_team=wu).count()
    away_games = Match.objects.filter(away_team=wu).count()
    total_games = home_games + away_games
    
    print(f"Total de jogos no banco: {total_games} (Casa: {home_games}, Fora: {away_games})")
    
    # 3. Listar algumas partidas para ver status e placar
    print("\n--- Últimos 10 jogos ---")
    matches = Match.objects.filter(home_team=wu) | Match.objects.filter(away_team=wu)
    for m in matches.order_by('-date')[:10]:
        print(f"{m.date} | {m.home_team.name} {m.home_score} x {m.away_score} {m.away_team.name} | Status: {m.status}")

except Team.DoesNotExist:
    print("ERRO: Time 'Western United' não encontrado no banco.")
except Exception as e:
    print(f"ERRO: {e}")
