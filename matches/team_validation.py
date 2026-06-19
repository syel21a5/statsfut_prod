"""
Team whitelists for each league to prevent API contamination
"""

LEAGUE_TEAM_WHITELISTS = {
    'Pro League': [
        # Belgian teams only
        'Royale Union SG', 'Union SG', 'Union Saint-Gilloise',
        'Sint-Truiden', 'Sint-Truidense VV',
        'Club Brugge', 'Club Brugge KV',
        'Gent', 'KAA Gent',
        'Mechelen', 'KV Mechelen',
        'Genk', 'KRC Genk',
        'Anderlecht', 'RSC Anderlecht',
        'Charleroi', 'Sporting Charleroi',
        'Westerlo', 'KVC Westerlo',
        'Antwerp', 'Royal Antwerp FC',
        'Zulte-Waregem', 'Zulte Waregem',
        'Standard Liege', 'Standard Liège', 'Standard de Liège',
        'OH Leuven', 'Oud-Heverlee Leuven',
        'La Louviere', 'RWDM Brussels',
        'Cercle Brugge', 'Cercle Brugge KSV',
        'Dender', 'FCV Dender EH',
        'Beerschot', 'Beerschot VA',
        'Kortrijk', 'KV Kortrijk',
        'Eupen', 'KAS Eupen',
        'Seraing', 'RFC Seraing',
        'Oostende', 'KV Oostende',
        'Mouscron', 'Royal Excel Mouscron',
    ],
    
    # Add more leagues as needed
    'Premier League': [
        'Arsenal',
        'Aston Villa',
        'Bournemouth',
        'Brentford',
        'Brighton',
        'Brighton & Hove Albion',
        'Chelsea',
        'Crystal Palace',
        'Everton',
        'Fulham',
        'Ipswich',
        'Ipswich Town',
        'Leicester',
        'Leicester City',
        'Liverpool',
        'Manchester City',
        'Man City',
        'Manchester United',
        'Man United',
        'Newcastle',
        'Newcastle Utd',
        'Newcastle United',
        'Nottingham Forest',
        'Nottm Forest',
        'Southampton',
        'Tottenham',
        'Tottenham Hotspur',
        'Spurs',
        'West Ham',
        'West Ham Utd',
        'West Ham United',
        'Wolverhampton',
        'Wolverhampton Wanderers',
        'Wolves',
        'Sheffield United',
        'Sheffield Utd',
        'Burnley',
        'Leeds',
        'Leeds Utd',
        'Norwich',
        'Watford',
    ],
    'La Liga': [],
    'Bundesliga': [],
    'Serie A': [],
    'Ligue 1': [
        'Angers', 'Auxerre', 'Brest', 'Le Havre', 'Lens', 'Lille', 'Lorient', 
        'Lyon', 'Marseille', 'Monaco', 'Montpellier', 'Nantes', 'Nice', 
        'PSG', 'Paris Saint-Germain', 'Paris SG', 'Reims', 'Rennes', 
        'Saint-Etienne', 'Strasbourg', 'RC Strasbourg', 'Toulouse'
    ],
    'A-League': [
        'Adelaide United', 'Auckland FC', 'Brisbane Roar', 'Central Coast Mariners',
        'Macarthur FC', 'Melbourne City', 'Melbourne Victory', 'Newcastle Jets',
        'Perth Glory', 'Sydney FC', 'Wellington Phoenix', 'Western Sydney Wanderers',
        'Western United'
    ],
    'Bundesliga': [
        # Austria
        'Austria Wien', 'Grazer AK', 'LASK Linz', 'Rapid Wien', 'Salzburg', 'RB Salzburg',
        'SCR Altach', 'Sturm Graz', 'TSV Hartberg', 'Wolfsberger AC', 'WSG Tirol', 'Austria Klagenfurt',
        'FC Blau-Weiss Linz', 'Ried', 'Lustenau',
        # Germany (Optional, but good to have)
        'Bayern Munich', 'Dortmund', 'Leverkusen', 'Leipzig', 'Stuttgart', 'Frankfurt'
    ],
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
        'Botafogo FC SP', 'Londrina EC',
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
