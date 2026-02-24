
import requests
import os
from django.conf import settings
from django.utils import timezone
from matches.models import Team, Match, League, Season, APIUsage
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

def log_api_usage(api_name, headers):
    try:
        rem = int(headers.get('x-requests-remaining', 0))
        used = int(headers.get('x-requests-used', 0))
        APIUsage.objects.update_or_create(
            api_name=api_name,
            defaults={'credits_remaining': rem, 'credits_used': used}
        )
        print(f"[{api_name}] Créditos: Restantes {rem} | Usados {used}")
        if rem < 50:
            print(f"[{api_name}] ATENÇÃO: Créditos críticos (<50)!")
    except Exception as e:
        print(f"Erro ao salvar uso da API: {e}")

import random

def fetch_live_odds_generic(league_name_db, country_db, sport_key, env_prefix, label):
    """
    Função genérica para buscar placares ao vivo na The Odds API.
    - league_name_db: Nome da liga no banco de dados (ex: 'Brasileirão', 'Liga Profesional')
    - country_db: País da liga no banco de dados (ex: 'Brasil', 'Argentina')
    - sport_key: Chave do esporte na API (ex: 'soccer_brazil_campeonato')
    - env_prefix: Prefixo das chaves no .env (ex: 'ODDS_API_KEY_BRAZIL_LIVE')
    - label: Nome para logs (ex: 'Brasil')
    """
    # 1. Coletar todas as chaves disponíveis para LIVE
    live_keys = []
    
    # Chave padrão (sem sufixo) - Opcional, mas checamos
    k1 = os.getenv(env_prefix)
    if k1: live_keys.append(k1)
    
    # Chaves extras (sufixo _1, _2, _3, etc.)
    i = 1
    while True:
        kn = os.getenv(f'{env_prefix}_{i}')
        if not kn:
            if i > 10: break # Limite de segurança
            i += 1
            continue # Tenta o próximo indice, vai que pulou um numero
        live_keys.append(kn)
        i += 1
        
    if not live_keys:
        print(f"ERRO: Nenhuma chave {env_prefix} encontrada no .env")
        return

    # 2. Escolher uma chave aleatória (Load Balancing)
    api_key = random.choice(live_keys)
    masked_key = api_key[:4] + "..." + api_key[-4:]
    
    print(f"[TheOddsAPI] Buscando placares ao vivo para {label} ({sport_key}) usando chave {masked_key}...")
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores/?daysFrom=1&apiKey={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        log_api_usage(f"The Odds API (Live - {label} - {masked_key})", response.headers)

        response.raise_for_status()
        matches_data = response.json()
        print(f"[TheOddsAPI] Encontrados {len(matches_data)} jogos na API para {label}.")
        
        # Get League
        league = League.objects.filter(name__icontains=league_name_db, country=country_db).first()
        if not league:
            # Tenta busca mais flexível
            league = League.objects.filter(name__icontains=league_name_db).first()
            
        if not league:
            print(f"[TheOddsAPI] Erro: Liga '{league_name_db}' ({country_db}) não encontrada no banco de dados.")
            return

        updates = 0
        for m in matches_data:
            home_name = m['home_team']
            away_name = m['away_team']
            completed = m.get('completed', False)
            scores = m.get('scores') # List like [{'name': 'Home', 'score': '1'}, ...]
            
            home_team = resolve_team(home_name, league)
            away_team = resolve_team(away_name, league)
            
            if not home_team or not away_team:
                print(f"[TheOddsAPI] Pulando time desconhecido em {label}: {home_name} vs {away_name}")
                continue
                
            match = Match.objects.filter(
                league=league,
                home_team=home_team,
                away_team=away_team,
                date__year=2026
            ).order_by('-date').first()
            
            if not match:
                # Tenta buscar jogo de 2025 também caso estejamos na virada ou dados antigos
                match = Match.objects.filter(
                    league=league,
                    home_team=home_team,
                    away_team=away_team,
                    date__year=2025
                ).order_by('-date').first()

            if not match:
                print(f"[TheOddsAPI] Jogo não encontrado no Banco de Dados ({label}): {home_team} vs {away_team}")
                continue

            # Parse Scores
            home_score = None
            away_score = None
            if scores:
                for s in scores:
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
                new_status = 'Scheduled'
            
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
                print(f"[TheOddsAPI] Atualizado ({label}): {home_team} {home_score}-{away_score} {away_team} ({new_status})")
                updates += 1
                
        print(f"[TheOddsAPI] Atualização ao vivo concluída para {label}. {updates} jogos atualizados.")
        
    except Exception as e:
        print(f"[TheOddsAPI] Erro ao buscar placares de {label}: {e}")

def fetch_live_odds_api_argentina():
    fetch_live_odds_generic(
        league_name_db="Liga Profesional",
        country_db="Argentina",
        sport_key="soccer_argentina_primera_division",
        env_prefix="ODDS_API_KEY_ARGENTINA_LIVE",
        label="Argentina"
    )

def fetch_live_odds_api_brazil():
    fetch_live_odds_generic(
        league_name_db="Brasileirão",
        country_db="Brasil",
        sport_key="soccer_brazil_campeonato",
        env_prefix="ODDS_API_KEY_BRAZIL_LIVE",
        label="Brasil"
    )

def fetch_live_odds_api_england():
    fetch_live_odds_generic(
        league_name_db="Premier League",
        country_db="Inglaterra",
        sport_key="soccer_epl",
        env_prefix="ODDS_API_KEY_ENGLAND_LIVE",
        label="Inglaterra"
    )

def fetch_live_odds_api_austria():
    fetch_live_odds_generic(
        league_name_db="Bundesliga",
        country_db="Austria",
        sport_key="soccer_austria_bundesliga",
        env_prefix="ODDS_API_KEY_AUSTRIA_LIVE",
        label="Austria"
    )


def fetch_upcoming_odds_api_argentina():
    """
    Busca próximos jogos da Liga Profesional (Argentina) usando a API de Upcoming (Chave 2).
    """
    api_key = os.getenv('ODDS_API_KEY_ARGENTINA_UPCOMING')
    if not api_key:
        print("ERRO: Chave ODDS_API_KEY_ARGENTINA_UPCOMING não configurada no .env")
        return

    sport_key = "soccer_argentina_primera_division"
    print(f"[TheOddsAPI] Buscando PRÓXIMOS JOGOS para {sport_key}...")
    
    # Endpoint /odds retorna jogos futuros
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

