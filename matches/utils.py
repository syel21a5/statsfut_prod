# Mapeamento centralizado de nomes de times para evitar duplicatas
# Formato: "Nome Incorreto/Alternativo": "Nome Padronizado"

TEAM_NAME_MAPPINGS = {
    # Premier League
    "Wolves": "Wolverhampton",
    "Man City": "Manchester City",
    "Man United": "Manchester Utd",
    "Man Utd": "Manchester Utd",
    "Newcastle": "Newcastle Utd",
    "Nott'm Forest": "Nottm Forest",
    "Nottingham": "Nottm Forest",
    "Nottingham Forest": "Nottm Forest",
    "Nottingham Forest FC": "Nottm Forest",
    "West Ham": "West Ham Utd",
    "Leeds": "Leeds Utd",
    "Leeds United": "Leeds Utd",
    "Sunderland AFC": "Sunderland",
    "AFC Bournemouth": "Bournemouth",
    "Ipswich": "Ipswich Town",
    "Sheffield Utd": "Sheffield United",
    "Sheff Utd": "Sheffield United",

    # Bundesliga (Alemanha)
    "Bayer 04 Leverkusen": "Leverkusen",
    "FC Bayern München": "Bayern Munich",
    "VfB Stuttgart": "Stuttgart",
    "RB Leipzig": "Leipzig",
    "Borussia Dortmund": "Dortmund",
    "Eintracht Frankfurt": "Frankfurt",
    "TSG 1899 Hoffenheim": "Hoffenheim",
    "1. FC Heidenheim 1846": "Heidenheim",
    "SV Werder Bremen": "Werder Bremen",
    "SC Freiburg": "Freiburg",
    "FC Augsburg": "Augsburg",
    "VfL Wolfsburg": "Wolfsburg",
    "1. FSV Mainz 05": "Mainz",
    "Borussia Mönchengladbach": "M Gladbach",
    "M'gladbach": "M Gladbach",
    "1. FC Union Berlin": "Union Berlin",
    "VfL Bochum 1848": "Bochum",
    "1. FC Köln": "Koln",
    "FC Koln": "Koln",
    "SV Darmstadt 98": "Darmstadt",
    "FC St. Pauli 1910": "St Pauli",
    "Holstein Kiel": "Holstein Kiel",
    "Hamburger SV": "Hamburg",
    "Hamburg SV": "Hamburg",
    "E. Frankfurt": "Frankfurt",
    "Ein Frankfurt": "Frankfurt",
    "Bayer Leverkusen": "Leverkusen",
    "FSV Mainz": "Mainz",

    # Pro League (Bélgica)
    "Union St.Gilloise": "Royale Union SG",
    "Union St.-Gilloise": "Royale Union SG",
    "Union Saint-Gilloise": "Royale Union SG",
    "St. Gilloise": "Royale Union SG",
    "St Gilloise": "Royale Union SG",
    "St. Truiden": "Sint-Truiden",
    "St Truiden": "Sint-Truiden",
    "Sint Truiden": "Sint-Truiden",
    "Waregem": "Zulte-Waregem",
    "Standard": "Standard Liege",
    "Standard Liège": "Standard Liege",
    "Standard de Liege": "Standard Liege",
    "Oud-Heverlee Leuven": "OH Leuven",
    "Oud Heverlee Leuven": "OH Leuven",
    "RAAL La Louviere": "La Louviere",
    "La Louvière": "La Louviere",
    "Cercle Brugge KSV": "Cercle Brugge",

    # Brasileirão (e times sul-americanos que aparecem em competições)
    "Flamengo RJ": "Flamengo",
    "Botafogo RJ": "Botafogo",
    "CA Mineiro": "Atletico-MG",
    "Atletico Mineiro": "Atletico-MG",
    "CA Paranaense": "Athletico-PR",
    "Club Athletico Paranaense": "Athletico-PR",
    "Coritiba FBC": "Coritiba",
    "Chapecoense AF": "Chapecoense",
    "Chapecoense-SC": "Chapecoense",
    "Clube do Remo": "Remo",
    "Mirassol FC": "Mirassol",
    "RB Bragantino": "Bragantino",
    "Red Bull Bragantino": "Bragantino",
    "Sao Paulo FC": "Sao Paulo",
    "Santos FC": "Santos",
    "Gremio FBPA": "Gremio",
    "Cruzeiro EC": "Cruzeiro",
    "EC Vitoria": "Vitoria",
    "Vasco da Gama": "Vasco",
    "Cuiaba Esporte Clube": "Cuiaba",
    "America FC": "America-MG", 
    "America MG": "America-MG",
    "Goias EC": "Goias",
    "Ceara SC": "Ceara",
    "Fortaleza EC": "Fortaleza",
    "EC Bahia": "Bahia",
    "Sport Club do Recife": "Sport Recife",
    "Avai FC": "Avai",
    "Juventude RS": "Juventude",
    "CSA": "CSA",
    "AC Goianiense": "Atletico-GO",
    "Atletico Goianiense": "Atletico-GO",
    "Criciuma EC": "Criciuma",
    "EC Juventude": "Juventude",
    "Fluminense FC": "Fluminense",
    "Botafogo FR": "Botafogo",
    "CR Vasco da Gama": "Vasco",
    "SC Corinthians Paulista": "Corinthians",
    "SE Palmeiras": "Palmeiras",
    
    # Argentina (Adicionar conforme necessário)
    # "River Plate ...": "River Plate",
}

COUNTRY_TRANSLATIONS = {
    "Inglaterra": "England",
    "Espanha": "Spain",
    "Alemanha": "Germany",
    "Italia": "Italy",
    "Franca": "France",
    "Holanda": "Netherlands",
    "Belgica": "Belgium",
    "Portugal": "Portugal",
    "Turquia": "Turkey",
    "Grecia": "Greece",
    "Austria": "Austria",
    "Brasil": "Brazil",
    "Argentina": "Argentina",
    "Australia": "Australia",
    "Suica": "Switzerland",
    "Republica Tcheca": "Czech Republic",
    "Dinamarca": "Denmark",
    "Finlandia": "Finland",
    "Noruega": "Norway",
    "Suecia": "Sweden",
    "Polonia": "Poland",
    "Ucrania": "Ukraine",
    "Russia": "Russia",
    "Japao": "Japan",
}

COUNTRY_REVERSE_TRANSLATIONS = {v.lower(): k for k, v in COUNTRY_TRANSLATIONS.items()}

def normalize_team_name(name):
    """
    Retorna o nome padronizado do time, se existir no mapeamento.
    Caso contrário, retorna o nome original limpo.
    """
    if not name:
        return None
    
    clean_name = name.strip()
    
    # Tenta busca exata (com strip)
    result = TEAM_NAME_MAPPINGS.get(clean_name)
    if result:
        return result
        
    # Tenta busca case-insensitive se necessário (opcional, mas seguro)
    # Por enquanto o strip já resolve 99% dos casos do CSV.
    return clean_name
