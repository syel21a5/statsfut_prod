
import requests
import os
from django.conf import settings
from django.utils import timezone
from matches.models import Team, Match, League, Season
from datetime import datetime
import pytz

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
    "Estudiantes": "Estudiantes L.P.", # Careful, might be Rio Cuarto? Usually Estudiantes LP is just Estudiantes
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
    "Independiente": "Independiente"
}

def resolve_team(name, league):
    # 1. Exact match
    t = Team.objects.filter(league=league, name__iexact=name).first()
    if t: return t
    
    # 2. Mapped match
    if name in ODDS_API_TEAM_MAPPINGS:
        mapped_name = ODDS_API_TEAM_MAPPINGS[name]
        t = Team.objects.filter(league=league, name__iexact=mapped_name).first()
        if t: return t
        
    # 3. Contains match
    t = Team.objects.filter(league=league, name__icontains=name).first()
    if t: return t
    
    return None

def fetch_live_odds_api_argentina():
    """
    Fetches live scores for Argentina Liga Profesional from The Odds API.
    Updates existing matches in the database.
    """
    api_key = getattr(settings, 'ODDS_API_KEY', os.getenv('ODDS_API_KEY', '386a173b7ca41f5a1362958a9eeeccdc'))
    sport_key = "soccer_argentina_primera_division"
    
    print(f"[TheOddsAPI] Fetching live scores for {sport_key}...")
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/?daysFrom=1&apiKey={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        
        # Monitoramento de Créditos
        remaining = int(response.headers.get('x-requests-remaining', 0))
        used = int(response.headers.get('x-requests-used', 0))
        print(f"[TheOddsAPI] Créditos: Usados {used} | Restantes {remaining}")
        if remaining < 50:
             print("[TheOddsAPI] ATENÇÃO: Créditos baixos! Considere pausar atualizações automáticas.")

        response.raise_for_status()
        matches_data = response.json()
        print(f"[TheOddsAPI] Found {len(matches_data)} matches.")
        
        # Get League
        league = League.objects.filter(name__icontains="Liga Profesional", country="Argentina").first()
        if not league:
            print("[TheOddsAPI] Error: League 'Liga Profesional' not found.")
            return

        updates = 0
        for m in matches_data:
            home_name = m['home_team']
            away_name = m['away_team']
            completed = m.get('completed', False)
            scores = m.get('scores') # List like [{'name': 'Home', 'score': '1'}, ...]
            last_update = m.get('last_update')
            
            home_team = resolve_team(home_name, league)
            away_team = resolve_team(away_name, league)
            
            if not home_team or not away_team:
                print(f"[TheOddsAPI] Skipping unknown team(s): {home_name} vs {away_name}")
                continue
                
            # Find Match in DB (approximate date check handled by filter or just finding the active match)
            # We look for matches in the last 48 hours or scheduled in next 24 hours
            # Actually, simpler to find by teams + season 2026
            
            match = Match.objects.filter(
                league=league,
                home_team=home_team,
                away_team=away_team,
                date__year=2026
            ).order_by('-date').first()
            
            if not match:
                # Maybe create it? Or just skip?
                # For live updates, we usually expect match to exist.
                # But if it doesn't, we could create it.
                # Let's skip for now to avoid duplicates if date is far off.
                print(f"[TheOddsAPI] Match not found in DB: {home_team} vs {away_team}")
                continue

            # Parse Scores
            home_score = None
            away_score = None
            if scores:
                for s in scores:
                    # 'name' usually matches home_team name or away_team name provided by API
                    # But careful with mapping.
                    # The Odds API returns 'name' same as 'home_team' field.
                    if s['name'] == home_name:
                        home_score = int(s['score'])
                    elif s['name'] == away_name:
                        away_score = int(s['score'])
            
            # Update Match
            changed = False
            
            if completed:
                new_status = 'Finished'
            elif scores: # Has scores but not completed -> Live (or HT)
                new_status = 'Live'
            else:
                new_status = 'Scheduled' # Or Keep existing if it was 'Time to be defined'
            
            # Only update status if it progresses (Scheduled -> Live -> Finished)
            # Or if we want to force sync.
            if match.status != 'Finished':
                if match.status != new_status:
                    match.status = new_status
                    changed = True
                
                if home_score is not None and match.home_score != home_score:
                    match.home_score = home_score
                    changed = True
                    
                if away_score is not None and match.away_score != away_score:
                    match.away_score = away_score
                    changed = True
            
            if changed:
                match.save()
                print(f"[TheOddsAPI] Updated: {home_team} {home_score}-{away_score} {away_team} ({new_status})")
                updates += 1
                
        print(f"[TheOddsAPI] Live update complete. {updates} matches updated.")
        
    except Exception as e:
        print(f"[TheOddsAPI] Error fetching live scores: {e}")

