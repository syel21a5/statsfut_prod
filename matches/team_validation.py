"""
Team whitelists for each league to prevent API contamination
"""

LEAGUE_TEAM_WHITELISTS = {
    'Brasileirao': [
        'Flamengo', 'Palmeiras', 'Atletico-MG', 'Athletico-PR', 'Fluminense',
        'Internacional', 'Sao Paulo', 'Santos', 'Corinthians', 'Gremio', 
        'Botafogo', 'Bahia', 'Fortaleza', 'Vasco', 'Cruzeiro',
        'Vitoria', 'Juventude', 'Cuiaba', 'Bragantino', 'Mirassol',
        'Sport Recife', 'Ceara', 'Atletico-GO', 'America-MG', 'Criciuma',
        # Nomes da API-Football
        'CA Mineiro', 'CA Paranaense', 'RB Bragantino', 'Red Bull Bragantino',
        'Botafogo FR', 'Grêmio FBPA', 'EC Bahia', 'EC Vitória', 'Cuiabá EC',
        'Fortaleza EC', 'Criciúma EC', 'AC Goianiense', 'CR Vasco da Gama',
        'Mirassol FC', 'Chapecoense AF', 'Goiás EC', 'Sport Club do Recife',
    ],
    'Série B': [
        # 20 times oficiais da Série B 2026 (fonte: SofaScore)
        'Sao Bernardo', 'Vila Nova', 'Sport Recife', 'Fortaleza',
        'Novorizontino', 'Criciuma', 'Nautico', 'Juventude',
        'Operario', 'Cuiaba', 'Athletic', 'Goias',
        'Atletico-GO', 'Ceara', 'CRB', 'Botafogo-SP',
        'Londrina', 'Avai', 'Ponte Preta', 'America-MG',
        # Nomes alternativos da API-Football
        'São Bernardo FC', 'Vila Nova FC', 'Sport Club do Recife',
        'Fortaleza EC', 'Criciúma EC', 'Nautico Recife', 'Náutico',
        'Operário Ferroviário', 'Operario-PR', 'Cuiabá EC', 'Cuiabá',
        'Athletic Club', 'Goiás EC', 'Goiás',
        'AC Goianiense', 'Atlético-GO',
        'Ceará', 'Clube De Regatas Brasil',
        'Botafogo FC SP', 'Londrina EC', 'Botafogo SP', 'Botafogo-SP',
        'Avaí FC', 'Avaí', 'América FC', 'América-MG',
    ],
}

def is_team_valid_for_league(team_name, league_name):
    """
    Check if a team name is valid for a given league
    Returns True if league has no whitelist or team is in whitelist
    """
    whitelist = LEAGUE_TEAM_WHITELISTS.get(league_name, [])
    
    # If no whitelist defined, accept all teams
    if not whitelist:
        return True
    
    # Check if team name matches any whitelist entry (case-insensitive, partial match)
    team_lower = team_name.lower()
    for valid_name in whitelist:
        if valid_name.lower() in team_lower or team_lower in valid_name.lower():
            return True
    
    return False
