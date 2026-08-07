import json

def generate_mysql_updates():
    try:
        with open('payload.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        rows = data['standings']['standings'][0]['rows']
        sofa_teams = {row['team']['name']: f"sofa_{row['team']['id']}" for row in rows}
    except Exception as e:
        print(f"Error reading payload.json: {e}")
        return

    # Precise mapping for Brasileirão 2026 teams
    # Source: User Screenshot -> SofaScore Payload
    mapping = {
        "Palmeiras": "Palmeiras",
        "Sao Paulo": "São Paulo",
        "Bahia": "Bahia",
        "Flamengo": "Flamengo",
        "Coritiba": "Coritiba",
        "Fluminense": "Fluminense",
        "Athletico-PR": "Athletico",
        "Corinthians": "Corinthians",
        "Bragantino": "Red Bull Bragantino",
        "Mirassol": "Mirassol",
        "Gremio": "Grêmio",
        "Chapecoense": "Chapecoense",
        "Atletico-MG": "Atlético Mineiro",
        "Santos": "Santos",
        "Vitoria": "Vitória",
        "Botafogo": "Botafogo",
        "Remo": "Remo",
        "Internacional": "Internacional",
        "Cruzeiro": "Cruzeiro",
        "Vasco": "Vasco da Gama",
        "America-MG": "América Mineiro",
        "Cuiaba": "Cuiabá",
        "Juventude": "Juventude",
        "Criciuma": "Criciúma",
        "Atletico-GO": "Atlético Goianiense",
    }

    updates = []
    
    for old_name, sofa_name in mapping.items():
        sofa_id = sofa_teams.get(sofa_name)
        if sofa_id:
            sql_sofa_name = sofa_name.replace("'", "''")
            sql_old_name = old_name.replace("'", "''")
            updates.append(f"UPDATE betstats.matches_team SET name = '{sql_sofa_name}', api_id = '{sofa_id}' WHERE name = '{sql_old_name}';")

    with open('update_teams_accurate.sql', 'w', encoding='utf-8') as f:
        f.write("\n".join(updates))
    
    print(f"Generated {len(updates)} update statements in update_teams_accurate.sql")

if __name__ == "__main__":
    generate_mysql_updates()
