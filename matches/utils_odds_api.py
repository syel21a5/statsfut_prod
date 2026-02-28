import os
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from matches.models import League, Team, Match, Season

# Manual Mappings for The Odds API -> DB Team Names
ODDS_API_TEAM_MAPPINGS = {
    "Central Córdoba (SdE)": "Central Cordoba",
    "Central Córdoba": "Central Cordoba",
    "Argentinos Juniors": "Argentinos Jrs",
    "Atlético Tucumán": "Atl. Tucuman",
    "Atlético Tucuman": "Atl. Tucuman",
    "Defensa y Justicia": "Defensa y Justicia",
    "Deportivo Riestra": "Dep. Riestra",
    "Estudiantes de La Plata": "Estudiantes L.P.",
    "Estudiantes": "Estudiantes L.P.",
    "Gimnasia La Plata": "Gimnasia L.P.",
    "Gimnasia y Esgrima (M)": "Gimnasia Mendoza",
    "Gimnasia y Esgrima (Mendoza)": "Gimnasia Mendoza",
    "Gimnasia Mendoza": "Gimnasia Mendoza",
    "Godoy Cruz": "Godoy Cruz", 
    "Huracán": "Huracan",
    "Atlético Huracán": "Huracan",
    "Independiente Rivadavia": "Ind. Rivadavia",
    "Instituto (Córdoba)": "Instituto",
    "Instituto de Córdoba": "Instituto",
    "Lanús": "Lanus",
    "Newell's Old Boys": "Newells Old Boys",
    "Newell's": "Newells Old Boys",
    "Sarmiento (Junín)": "Sarmiento Junin",
    "Sarmiento de Junin": "Sarmiento Junin",
    "Sarmiento": "Sarmiento Junin",
    "Talleres (Córdoba)": "Talleres Cordoba",
    "Talleres": "Talleres Cordoba",
    "Unión (Santa Fe)": "Union de Santa Fe",
    "Unión": "Union de Santa Fe",
    "Union Santa Fe": "Union de Santa Fe",
    "Vélez Sarsfield": "Velez Sarsfield",
    "Vélez": "Velez Sarsfield",
    "Velez Sarsfield BA": "Velez Sarsfield",
    "Barracas Central": "Barracas Central",
    "Banfield": "Banfield",
    "Belgrano": "Belgrano",
    "Belgrano de Cordoba": "Belgrano",
    "Boca Juniors": "Boca Juniors",
    "Platense": "Platense",
    "Racing Club": "Racing Club",
    "River Plate": "River Plate",
    "Rosario Central": "Rosario Central",
    "San Lorenzo": "San Lorenzo",
    "Tigre": "Tigre",
    "CA Tigre BA": "Tigre",
    "Estudiantes Río Cuarto": "Estudiantes Rio Cuarto",
    "Estudiantes de Río Cuarto": "Estudiantes Rio Cuarto",
    "Estudiantes (RC)": "Estudiantes Rio Cuarto",
    "Aldosivi": "Aldosivi",
    "Aldosivi Mar del Plata": "Aldosivi",
    "Independiente": "Independiente",

    # --- ENGLAND ---
    "Wolverhampton Wanderers": "Wolverhampton",
    "Newcastle United": "Newcastle Utd",
    "West Ham United": "West Ham Utd",
    "Leeds United": "Leeds Utd",
    "Brighton and Hove Albion": "Brighton",
    "Nottingham Forest": "Nottm Forest",
    "Manchester United": "Manchester Utd",
    "Tottenham Hotspur": "Tottenham",
    "Sheffield United": "Sheffield Utd",
    "Leicester City": "Leicester",

    # --- AUSTRIA ---
    "Red Bull Salzburg": "RB Salzburg",
    "Salzburg": "RB Salzburg",
    "Sturm Graz": "Sturm Graz",
    "LASK Linz": "LASK",
    "LASK": "LASK",
    "Austria Wien": "Austria Vienna",
    "Austria Vienna": "Austria Vienna",
    "Rapid Wien": "Rapid Vienna",
    "Rapid Vienna": "Rapid Vienna",
    "Hartberg": "Hartberg",
    "TSV Hartberg": "Hartberg",
    "Altach": "Altach",
    "SCR Altach": "Altach",
    "Ried": "Ried",
    "SV Ried": "Ried",
    "Wolfsberger AC": "Wolfsberger AC",
    "Wolfsberg": "Wolfsberger AC",
    "Tirol": "Tirol",
    "WSG Tirol": "Tirol",
    "Grazer AK": "Grazer AK",
    "Grazer AK 1902": "Grazer AK",
    "GAK": "Grazer AK",
    "Blau Weiss Linz": "Blau-Weiss Linz",
    "BW Linz": "Blau-Weiss Linz",
    "Blau-Weiss Linz": "Blau-Weiss Linz",
    "FC Blau-Weiß Linz": "Blau-Weiss Linz",
    "Rheindorf Altach": "Altach",
    
    # --- AUSTRALIA ---
    "Adelaide Utd": "Adelaide United",
    "WS Wanderers": "Western Sydney Wanderers",
    "Melbourne V.": "Melbourne Victory",
    "Auckland": "Auckland FC",
    "Wellington": "Wellington Phoenix FC",
    "Central Coast": "Central Coast Mariners",
    "Newcastle Jets": "Newcastle Jets FC",
    "Macarthur": "Macarthur FC",
    "Sydney": "Sydney FC",
    "Brisbane": "Brisbane Roar",
    "Melbourne C.": "Melbourne City",
    "Western Utd": "Western United",
    "Western United FC": "Western United",

    # --- BELGIUM ---
    "Union Saint-Gilloise": "Royale Union SG",
    "Union SG": "Royale Union SG",
    "Royal Antwerp": "Antwerp",
    "Antwerp": "Antwerp",
    "Standard Liège": "Standard Liege",
    "Standard": "Standard Liege",
    "KV Mechelen": "KV Mechelen",
    "Mechelen": "KV Mechelen",
    "Sint-Truidense": "Sint-Truiden",
    "STVV": "Sint-Truiden",
    "Oud-Heverlee Leuven": "OH Leuven",
    "Leuven": "OH Leuven",
    "KV Kortrijk": "KV Kortrijk",
    "Kortrijk": "KV Kortrijk",
    "KVC Westerlo": "Westerlo",
    "Beerschot VA": "Beerschot",
    "Beerschot": "Beerschot",
    "Cercle Brugge KSV": "Cercle Brugge",
    "Cercle Brugge": "Cercle Brugge",
    "KAA Gent": "Gent",
    "Gent": "Gent",
    "KRC Genk": "KRC Genk",
    "Genk": "KRC Genk",
    "Club Brugge KV": "Club Brugge",
    "Club Brugge": "Club Brugge",
    "FC Dender": "Dender",
    "Dender": "Dender",
    "Zulte Waregem": "Zulte-Waregem",
    "SV Zulte-Waregem": "Zulte-Waregem",
    "Waregem": "Zulte-Waregem",
    "KV Oostende": "KV Oostende",
    "Oostende": "KV Oostende",
    "RWDM": "RWD Molenbeek",
    "RWD Molenbeek": "RWD Molenbeek",
    "Sint Truiden": "Sint-Truiden",
    "Royal Antwerp": "Antwerp",
    "RAAL La Louvière": "RAAL La Louvière", # New team 2024/25?

    # --- ALEMANHA ---
    "Bayern Munich": "Bayern Munich",
    "Bayern München": "Bayern Munich",
    "FC Bayern München": "Bayern Munich",
    "Borussia Dortmund": "Dortmund",
    "Dortmund": "Dortmund",
    "RB Leipzig": "Leipzig",
    "Leipzig": "Leipzig",
    "Bayer Leverkusen": "Leverkusen",
    "Leverkusen": "Leverkusen",
    "Eintracht Frankfurt": "Frankfurt",
    "Frankfurt": "Frankfurt",
    "SC Freiburg": "Freiburg",
    "Freiburg": "Freiburg",
    "VfB Stuttgart": "Stuttgart",
    "Stuttgart": "Stuttgart",
    "TSG Hoffenheim": "Hoffenheim",
    "Hoffenheim": "Hoffenheim",
    "1899 Hoffenheim": "Hoffenheim",
    "Borussia Mönchengladbach": "M Gladbach",
    "Borussia Monchengladbach": "M Gladbach",
    "M'gladbach": "M Gladbach",
    "Gladbach": "M Gladbach",
    "VfL Wolfsburg": "Wolfsburg",
    "Wolfsburg": "Wolfsburg",
    "FSV Mainz 05": "Mainz",
    "Mainz 05": "Mainz",
    "Mainz": "Mainz",
    "FC Augsburg": "Augsburg",
    "Augsburg": "Augsburg",
    "1. FC Union Berlin": "Union Berlin",
    "Union Berlin": "Union Berlin",
    "Werder Bremen": "Werder Bremen",
    "SV Werder Bremen": "Werder Bremen",
    "1. FC Köln": "Koln",
    "1. FC Koln": "Koln",
    "Koln": "Koln",
    "Cologne": "Koln",
    "VfL Bochum": "Bochum",
    "Bochum": "Bochum",
    "1. FC Heidenheim": "Heidenheim",
    "Heidenheim": "Heidenheim",
    "Darmstadt 98": "Darmstadt",
    "SV Darmstadt 98": "Darmstadt",
    "Darmstadt": "Darmstadt",
    "FC St. Pauli": "St Pauli",
    "St. Pauli": "St Pauli",
    "St Pauli": "St Pauli",
    "Holstein Kiel": "Holstein Kiel",
    "Hamburger SV": "Hamburg",
    "Hamburg": "Hamburg",
    "Greuther Fürth": "Greuther Furth",
    "Greuther Furth": "Greuther Furth",
    "Arminia Bielefeld": "Bielefeld",
    "Bielefeld": "Bielefeld",
    "Paderborn": "Paderborn",
    "SC Paderborn 07": "Paderborn",
    "Fortuna Düsseldorf": "Fortuna Dusseldorf",
    "Fortuna Dusseldorf": "Fortuna Dusseldorf",

    # --- SUICA ---
    "FC Thun": "Thun",
    "FC Luzern": "Luzern",
    "FC St Gallen": "St. Gallen",
    "FC Winterthur": "Winterthur",
    "FC Sion": "Sion",
    "FC Lausanne-Sport": "Lausanne",
    "FC Basel": "Basel",
    "BSC Young Boys": "Young Boys",
    "FC Zurich": "Zurich",
    "Grasshopper Zürich": "Grasshoppers",
    "Grasshopper Club Zurich": "Grasshoppers",
    "FC Lugano": "Lugano",
    "Yverdon-Sport FC": "Yverdon",
    "Stade Lausanne-Ouchy": "Lausanne Ouchy",
    "Servette FC": "Servette",
    "Servette": "Servette",
    "Lausanne-Sport": "Lausanne",
    "St. Gallen": "St. Gallen",
    "Winterthur": "Winterthur",
    "Luzern": "Luzern",
    "Lugano": "Lugano",
    "Basel": "Basel",
    "Zurich": "Zurich",
    "Young Boys": "Young Boys",
    "Sion": "Sion",
    "Thun": "Thun",
}

def resolve_team(name, league):
    """
    Resolve nome do time usando mapeamento manual ou busca no banco.
    """
    # 1. Check manual mapping
    if name in ODDS_API_TEAM_MAPPINGS:
        mapped_name = ODDS_API_TEAM_MAPPINGS[name]
        team = Team.objects.filter(name__iexact=mapped_name, league=league).first()
        if team:
            return team

    # 2. Direct match
    team = Team.objects.filter(name__iexact=name, league=league).first()
    if team:
        return team
        
    # 3. Contains match (risky but useful)
    team = Team.objects.filter(name__icontains=name, league=league).first()
    if team:
        return team
        
    # 4. Try normalized name
    # from .utils import normalize_team_name
    # normalized = normalize_team_name(name)
    # team = Team.objects.filter(name__iexact=normalized, league=league).first()
    
    return None

def log_api_usage(api_name, headers):
    try:
        remaining = headers.get('x-requests-remaining') or headers.get('X-Requests-Remaining')
        used = headers.get('x-requests-used') or headers.get('X-Requests-Used')
        
        if remaining:
            from matches.models import APIUsage
            obj, _ = APIUsage.objects.get_or_create(api_name=api_name)
            obj.credits_remaining = int(remaining)
            if used:
                obj.credits_used = int(used)
            obj.save()
            print(f"[API] {api_name} - Remaining: {remaining}")
    except Exception as e:
        print(f"[API] Falha ao logar uso: {e}")

def fetch_upcoming_odds_api_belgium():
    """
    Busca próximos jogos da Pro League (Belgica) usando a API de Upcoming (Chave Reutilizada).
    Cria times e partidas se não existirem.
    """
    api_key = os.getenv('ODDS_API_KEY_BELGIUM_UPCOMING')
    if not api_key:
        print("ERRO: Chave ODDS_API_KEY_BELGIUM_UPCOMING não configurada no .env")
        return

    sport_key = "soccer_belgium_first_div"
    print(f"[TheOddsAPI] Buscando PRÓXIMOS JOGOS para {sport_key}...")
    
    # Endpoint /odds retorna jogos futuros
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h"
    
    try:
        response = requests.get(url, timeout=10)
        log_api_usage("The Odds API (Upcoming - Belgium)", response.headers)

        response.raise_for_status()
        matches_data = response.json()
        print(f"[TheOddsAPI] Encontrados {len(matches_data)} jogos futuros.")
        
        # Tenta encontrar a liga (pode ser "Pro League" ou "Jupiler Pro League")
        league = League.objects.filter(name__icontains="Pro League", country="Belgica").first()
        if not league:
            # Fallback for country "Belgium" if "Belgica" fails (setup script used "Belgica")
            league = League.objects.filter(name__icontains="Pro League", country="Belgium").first()
            
        if not league:
            print("ERRO: Liga Pro League (Belgica) não encontrada no banco.")
            return

        # Ajuste para season corrente (2024/2025 -> 2025)
        season, _ = Season.objects.get_or_create(year=2025)
        creates = 0
        updates = 0

        for m in matches_data:
            commence_time = m['commence_time'].replace('Z', '+00:00')
            dt_obj = datetime.fromisoformat(commence_time)
            
            home_team = resolve_team(m['home_team'], league)
            away_team = resolve_team(m['away_team'], league)
            
            if not home_team or not away_team:
                print(f"Skipping match due to unresolved team: {m['home_team']} vs {m['away_team']}")
                continue

            # Check existence
            start_window = dt_obj - timezone.timedelta(hours=24)
            end_window = dt_obj + timezone.timedelta(hours=24)
            
            match = Match.objects.filter(
                league=league,
                home_team=home_team,
                away_team=away_team,
                date__range=(start_window, end_window)
            ).first()

            if match:
                # Update time if needed
                time_diff = abs((match.date - dt_obj).total_seconds())
                if time_diff > 3600:
                    match.date = dt_obj
                    match.status = 'Scheduled'
                    match.save()
                    updates += 1
            else:
                Match.objects.create(
                    league=league,
                    season=season,
                    home_team=home_team,
                    away_team=away_team,
                    date=dt_obj,
                    status='Scheduled'
                )
                creates += 1
        
        print(f"[TheOddsAPI] Próximos jogos: {creates} criados, {updates} atualizados.")

    except Exception as e:
        print(f"[TheOddsAPI] Erro ao buscar próximos jogos: {e}")

def fetch_upcoming_odds_api_argentina():
    """
    Busca próximos jogos da Liga Profesional (Argentina) usando a API de Upcoming.
    """
    api_key = os.getenv('ODDS_API_KEY_ARGENTINA_UPCOMING')
    if not api_key:
        print("ERRO: Chave ODDS_API_KEY_ARGENTINA_UPCOMING não configurada no .env")
        return

    sport_key = "soccer_argentina_primera_division"
    print(f"[TheOddsAPI] Buscando PRÓXIMOS JOGOS para {sport_key}...")
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h"
    
    try:
        response = requests.get(url, timeout=10)
        log_api_usage("The Odds API (Upcoming - Argentina)", response.headers)

        response.raise_for_status()
        matches_data = response.json()
        print(f"[TheOddsAPI] Encontrados {len(matches_data)} jogos futuros.")
        
        league = League.objects.filter(name__icontains="Liga Profesional", country="Argentina").first()
        if not league:
            return

        season, _ = Season.objects.get_or_create(year=2026)
        creates = 0
        updates = 0

        for m in matches_data:
            commence_time = m['commence_time'].replace('Z', '+00:00')
            dt_obj = datetime.fromisoformat(commence_time)
            
            home_team = resolve_team(m['home_team'], league)
            away_team = resolve_team(m['away_team'], league)
            
            if not home_team or not away_team:
                continue

            start_window = dt_obj - timezone.timedelta(hours=24)
            end_window = dt_obj + timezone.timedelta(hours=24)
            
            match = Match.objects.filter(
                league=league,
                home_team=home_team,
                away_team=away_team,
                date__range=(start_window, end_window)
            ).first()

            if match:
                time_diff = abs((match.date - dt_obj).total_seconds())
                if time_diff > 3600:
                    match.date = dt_obj
                    match.status = 'Scheduled'
                    match.save()
                    updates += 1
            else:
                Match.objects.create(
                    league=league,
                    season=season,
                    home_team=home_team,
                    away_team=away_team,
                    date=dt_obj,
                    status='Scheduled'
                )
                creates += 1
        
        print(f"[TheOddsAPI] Próximos jogos: {creates} criados, {updates} atualizados.")

    except Exception as e:
        print(f"[TheOddsAPI] Erro ao buscar próximos jogos: {e}")

def fetch_upcoming_odds_api_australia():
    """
    Busca próximos jogos da A-League (Australia) usando a API de Upcoming.
    """
    api_key = os.getenv('ODDS_API_KEY_AUSTRALIA_UPCOMING')
    if not api_key:
        print("ERRO: Chave ODDS_API_KEY_AUSTRALIA_UPCOMING não configurada no .env")
        return

    sport_key = "soccer_australia_aleague"
    print(f"[TheOddsAPI] Buscando PRÓXIMOS JOGOS para {sport_key}...")
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h"
    
    try:
        response = requests.get(url, timeout=10)
        log_api_usage("The Odds API (Upcoming - Australia)", response.headers)

        response.raise_for_status()
        matches_data = response.json()
        print(f"[TheOddsAPI] Encontrados {len(matches_data)} jogos futuros.")
        
        league = League.objects.filter(name__icontains="A League", country="Australia").first()
        if not league:
            return

        season, _ = Season.objects.get_or_create(year=2026)
        creates = 0
        updates = 0

        for m in matches_data:
            commence_time = m['commence_time'].replace('Z', '+00:00')
            dt_obj = datetime.fromisoformat(commence_time)
            
            home_team = resolve_team(m['home_team'], league)
            away_team = resolve_team(m['away_team'], league)
            
            if not home_team or not away_team:
                continue

            start_window = dt_obj - timezone.timedelta(hours=24)
            end_window = dt_obj + timezone.timedelta(hours=24)
            
            match = Match.objects.filter(
                league=league,
                home_team=home_team,
                away_team=away_team,
                date__range=(start_window, end_window)
            ).first()

            if match:
                time_diff = abs((match.date - dt_obj).total_seconds())
                if time_diff > 3600:
                    match.date = dt_obj
                    match.status = 'Scheduled'
                    match.save()
                    updates += 1
            else:
                Match.objects.create(
                    league=league,
                    season=season,
                    home_team=home_team,
                    away_team=away_team,
                    date=dt_obj,
                    status='Scheduled'
                )
                creates += 1
        
        print(f"[TheOddsAPI] Próximos jogos: {creates} criados, {updates} atualizados.")

    except Exception as e:
        print(f"[TheOddsAPI] Erro ao buscar próximos jogos: {e}")

# --- PLACEHOLDERS FOR DISABLED LIVE APIS ---

def fetch_live_odds_api_argentina():
    print("[TheOddsAPI] Live API Argentina is DISABLED/RESERVED.")

def fetch_live_odds_api_brazil():
    print("[TheOddsAPI] Live API Brazil is DISABLED/RESERVED.")

def fetch_live_odds_api_england():
    print("[TheOddsAPI] Live API England is DISABLED/RESERVED.")

def fetch_live_odds_api_austria():
    print("[TheOddsAPI] Live API Austria is DISABLED/RESERVED.")

def fetch_live_odds_api_australia():
    print("[TheOddsAPI] Live API Australia is DISABLED/RESERVED.")
