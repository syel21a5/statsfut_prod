import json
import os
import time
from curl_cffi import requests

def sync_switzerland():
    # 1. SofaScore Teams from Payload 2025/26
    try:
        with open('payload.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        rows = data['standings']['standings'][0]['rows']
        sofa_teams = {row['team']['name']: row['team']['id'] for row in rows}
    except Exception as e:
        print(f"Erro payload: {e}")
        return

    # 2. Precise mapping (DB Name -> Sofa Name)
    mapping = {
        "Young Boys": "BSC Young Boys",
        "BSC Young Boys": "BSC Young Boys",
        "Basel": "Basel",
        "Lugano": "FC Lugano",
        "FC Lugano": "FC Lugano",
        "Luzern": "FC Luzern",
        "FC Luzern": "FC Luzern",
        "Sion": "FC Sion",
        "FC Sion": "FC Sion",
        "St. Gallen": "FC St. Gallen 1879",
        "FC St. Gallen 1879": "FC St. Gallen 1879",
        "Zurich": "FC Zürich",
        "FC Zürich": "FC Zürich",
        "Servette": "Servette FC",
        "Servette FC": "Servette FC",
        "Winterthur": "FC Winterthur",
        "FC Winterthur": "FC Winterthur",
        "Grasshoppers": "Grasshopper Club Zürich",
        "Grasshopper Club Zürich": "Grasshopper Club Zürich",
        "Lausanne": "FC Lausanne-Sport",
        "FC Lausanne-Sport": "FC Lausanne-Sport",
        "Thun": "FC Thun",
        "FC Thun": "FC Thun",
        "Yverdon": "Yverdon-Sport",
    }

    # 3. Generate SQL
    updates = []
    for db_name, sofa_name in mapping.items():
        sofa_id = sofa_teams.get(sofa_name)
        if sofa_id:
            sql_sofa_name = sofa_name.replace("'", "''")
            sql_db_name = db_name.replace("'", "''")
            updates.append(f"UPDATE betstats.matches_team SET name = '{sql_sofa_name}', api_id = 'sofa_{sofa_id}' WHERE name = '{sql_db_name}' AND league_id = 42;")

    with open('update_switzerland_teams.sql', 'w', encoding='utf-8') as f:
        f.write("\n".join(updates))
    print(f"SQL gerado: {len(updates)} updates.")

    # 4. Download logos using curl_cffi to bypass 403
    base_static = os.path.join('static', 'teams', 'suica', 'super-league')
    os.makedirs(base_static, exist_ok=True)
    
    session = requests.Session(impersonate="chrome110")
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    })

    for sofa_name, sofa_id in sofa_teams.items():
        file_path = os.path.join(base_static, f"sofa_{sofa_id}.png")
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            continue
            
        url = f"https://api.sofascore.app/api/v1/team/{sofa_id}/image"
        print(f"Baixando logo: {sofa_name} (ID: {sofa_id})...")
        try:
            res = session.get(url, timeout=15)
            if res.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(res.content)
                print(f"    OK!")
            else:
                print(f"    Falha: Status {res.status_code}")
            time.sleep(1)
        except Exception as e:
            print(f"    Erro ao baixar {sofa_name}: {e}")

if __name__ == "__main__":
    sync_switzerland()
