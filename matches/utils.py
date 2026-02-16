# Mapeamento centralizado de nomes de times para evitar duplicatas
# Formato: "Nome Incorreto/Alternativo": "Nome Padronizado"

TEAM_NAME_MAPPINGS = {
    # Premier League
    "Wolves": "Wolverhampton",
    "Man City": "Manchester City",
    "Man United": "Manchester Utd",
    "Newcastle": "Newcastle Utd",
    "Nott'm Forest": "Nottm Forest",
    "West Ham": "West Ham Utd",
    "Leeds": "Leeds Utd",
    "Sunderland AFC": "Sunderland",
    "Nottingham Forest FC": "Nottm Forest",

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
    "Brasil": "Brazil",
    "Argentina": "Argentina",
}

COUNTRY_REVERSE_TRANSLATIONS = {v: k for k, v in COUNTRY_TRANSLATIONS.items()}

def normalize_team_name(name):
    """
    Retorna o nome padronizado do time, se existir no mapeamento.
    Caso contrário, retorna o nome original limpo.
    """
    if not name:
        return None
    
    clean_name = name.strip()
    return TEAM_NAME_MAPPINGS.get(clean_name, clean_name)
