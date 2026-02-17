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
    'Premier League': [],  # Empty = accept all (already validated by league assignment)
    'La Liga': [],
    'Bundesliga': [],
    'Serie A': [],
    'Ligue 1': [],
    'Brasileirao': [],
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
