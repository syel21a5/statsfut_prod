from matches.models import Team, League

def undo_wrong_teams():
    # A API 73 na verdade era a Copa do Brasil e não a Série C.
    # Por isso ela criou vários times da Série A/B dentro da Série C no banco.
    # Vamos pegar a liga Série C
    db_league = League.objects.filter(name__icontains='Série C').first()
    if not db_league:
        print("Liga Série C não encontrada!")
        return

    # Lista dos times criados erroneamente hoje
    wrong_teams = [
        "CRB", "Porto BA", "Figueirense", "Azuriz", "Nova Iguaçu", "Lagarto",
        "Velo Clube", "Vila Nova", "Tuna Luso", "Tocantinópolis", "Avai",
        "Porto Vitória", "Betim", "Operario-PR", "Capital", "Manaus FC",
        "Rio Branco ES", "Santa Catarina", "Cuiaba", "Ivinhema", "Manauara",
        "America Mineiro", "Tirol/CEFAT", "Trem", "Fluminense PI",
        "Portuguesa RJ", "Maracanã", "Desportiva ES", "Sport Recife",
        "Juventude", "Guaporé", "Santa Cruz", "Sousa", "Joinville",
        "Ponte Preta", "Guarany de Bagé", "Goias", "America-RN",
        "Uberlandia", "Ypiranga-RS", "Fortaleza EC", "Castanhal",
        "Jacuipense", "Porto Velho", "Atletico Goianiense", "Madureira",
        "Águia de Marabá", "Operario Ferroviario", "Capital Brasilia",
        "Ceara", "Mixto", "Novorizontino", "Chapecoense-sc", "Sao Paulo",
        "Gremio", "Vasco DA Gama", "Corinthians", "Bahia", "Cruzeiro",
        "Santos", "Coritiba", "Internacional", "Flamengo", "RB Bragantino",
        "Mirassol", "Atletico-MG", "Palmeiras", "Atletico Paranaense"
    ]

    deleted_count = 0
    for team_name in wrong_teams:
        # Busca o time exato naquela liga específica
        team = Team.objects.filter(name=team_name, league=db_league)
        if team.exists():
            team.delete()
            print(f"Apagado com sucesso: {team_name} da Série C")
            deleted_count += 1
            
    # E para os dois da Liga Profesional e Primera Division que deram erro:
    Team.objects.filter(name="Central Cordoba de Santiago", league__name__icontains="Liga Profesional").delete()
    Team.objects.filter(name="Deportes Limache", league__name__icontains="Primera Division").delete()
            
    print(f"\nFinalizado! {deleted_count} times apagados da Série C.")

undo_wrong_teams()
