from matches.models import Team, League

def undo_wrong_teams():
    db_league = League.objects.filter(name__icontains='Série C').first()
    if not db_league:
        print("Liga Série C não encontrada!")
        return

    # Lista dos times femininos criados erroneamente hoje
    wrong_teams = [
        "Botafogo W", "Flamengo W", "Palmeiras W", "Corinthians W", 
        "America Mineiro W", "Juventude W", "Santos W", "Mixto W", 
        "Internacional RS W", "RB Bragantino W", "Cruzeiro W", 
        "Atlético Mineiro W", "São Paulo W", "Ferroviaria W", "Gremio W", 
        "Fluminense W", "Bahia W", "Ec Vitoria W", "Vitória BA W"
    ]

    deleted_count = 0
    for team_name in wrong_teams:
        team = Team.objects.filter(name=team_name, league=db_league)
        if team.exists():
            team.delete()
            print(f"Apagado com sucesso: {team_name} da Série C")
            deleted_count += 1
            
    print(f"\nFinalizado! {deleted_count} times femininos apagados da Série C.")

undo_wrong_teams()
