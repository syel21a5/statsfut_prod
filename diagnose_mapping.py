"""
Diagnóstico Completo: Compara TODOS os times do banco com TODOS os times da API.
Gera um relatório detalhado para revisão manual antes de aplicar qualquer mudança.
Roda no Docker local, gasta créditos apenas da chave local (não do servidor).
"""
import os
import sys
import json
import time
import difflib
import unicodedata

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

import requests
from matches.models import League, Team

API_KEY = os.getenv('API_FOOTBALL_KEY', '')
HEADERS = {'x-apisports-key': API_KEY}
BASE_URL = 'https://v3.football.api-sports.io'

TEAM_ALIASES = {
    'odds bk': 'odd ballklubb',
    'stabaek fotball': 'stabaek',
    'hodd il': 'hodd',
    'asane': 'asane',
    'strommen if': 'strommen',
    'ranheim il': 'ranheim',
    'moss fk': 'moss',
    'sogndal il': 'sogndal',
    'bryne fk': 'bryne',
    'lyn fk': 'lyn',
    'sandnes ulf': 'sandnes ulf',
    'arsenal sarandi': 'arsenal de sarandi',
    'godoy cruz': 'godoy cruz',
    'san martin s.j.': 'san martin de san juan',
    'san martin t.': 'san martin de tucuman',
}

def normalize_name(name):
    n = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8').lower().strip()
    n = n.replace('-', ' ')
    return TEAM_ALIASES.get(n, n)

def get_api_teams(league_api_id, season=2026):
    """Puxa todos os times de uma liga na API"""
    url = f"{BASE_URL}/teams?league={league_api_id}&season={season}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        if data.get('errors'):
            # Tenta temporada anterior
            if season > 2024:
                return get_api_teams(league_api_id, season - 1)
            return []
        return [{'id': t['team']['id'], 'name': t['team']['name']} for t in data.get('response', [])]
    except Exception as e:
        print(f"  ERRO ao buscar times: {e}")
        return []

def main():
    leagues_with_api = League.objects.filter(api_id__isnull=False).order_by('country', 'name')
    
    if not leagues_with_api.exists():
        print("Nenhuma liga com api_id encontrada!")
        return

    report = {}
    total_credits = 0
    
    print(f"\n{'='*80}")
    print(f"DIAGNÓSTICO COMPLETO DE MAPEAMENTO DE TIMES")
    print(f"{'='*80}")
    print(f"Total de ligas mapeadas: {leagues_with_api.count()}\n")

    for league in leagues_with_api:
        print(f"\n{'─'*60}")
        print(f"Liga: {league.name} | País: {league.country} | API ID: {league.api_id}")
        print(f"{'─'*60}")
        
        # Buscar times da API
        api_teams = get_api_teams(league.api_id)
        total_credits += 1
        time.sleep(0.3)
        
        if not api_teams:
            print(f"  ⚠ API não retornou times para esta liga (API ID: {league.api_id})")
            report[league.name] = {'status': 'SEM_DADOS_API', 'api_id': league.api_id}
            continue
        
        # Buscar times do banco para esta liga
        db_teams = Team.objects.filter(league=league)
        
        if not db_teams.exists():
            print(f"  ⚠ Nenhum time no banco para esta liga")
            report[league.name] = {'status': 'SEM_TIMES_BANCO'}
            continue
        
        league_report = {
            'api_id': league.api_id,
            'country': league.country,
            'mapped': [],
            'unmapped': [],
            'already_ok': [],
        }
        
        for db_t in db_teams:
            # Se já tem api_id, verificar se está correto
            if db_t.api_id:
                api_match = next((a for a in api_teams if str(a['id']) == str(db_t.api_id)), None)
                if api_match:
                    league_report['already_ok'].append({
                        'db_name': db_t.name,
                        'db_id': db_t.id,
                        'api_name': api_match['name'],
                        'api_id': api_match['id'],
                    })
                    print(f"  ✅ JÁ OK: {db_t.name} (DB:{db_t.id}) = {api_match['name']} (API:{api_match['id']})")
                    continue
            
            # Tentar mapear por similaridade de nome
            db_norm = normalize_name(db_t.name)
            best_match = None
            best_score = 0
            
            for api_t in api_teams:
                api_norm = normalize_name(api_t['name'])
                score = difflib.SequenceMatcher(None, db_norm, api_norm).ratio()
                if score > best_score:
                    best_score = score
                    best_match = api_t
            
            entry = {
                'db_name': db_t.name,
                'db_id': db_t.id,
                'api_name': best_match['name'] if best_match else 'NENHUM',
                'api_id': best_match['id'] if best_match else None,
                'score': round(best_score * 100, 1),
            }
            
            if best_score > 0.60:
                league_report['mapped'].append(entry)
                emoji = '✓' if best_score > 0.80 else '⚡'
                print(f"  {emoji} MAPEÁVEL ({entry['score']}%): '{db_t.name}' → '{best_match['name']}' (API:{best_match['id']})")
            else:
                league_report['unmapped'].append(entry)
                print(f"  ❌ NÃO MAPEADO ({entry['score']}%): '{db_t.name}' → Mais próximo: '{best_match['name']}' (API:{best_match['id']})")
        
        report[league.name] = league_report
    
    # RESUMO FINAL
    print(f"\n\n{'='*80}")
    print(f"RESUMO FINAL")
    print(f"{'='*80}")
    
    total_ok = 0
    total_mappable = 0
    total_unmapped = 0
    problem_leagues = []
    
    for league_name, data in report.items():
        if isinstance(data, dict) and 'mapped' in data:
            ok = len(data['already_ok'])
            mapped = len(data['mapped'])
            unmapped = len(data['unmapped'])
            total_ok += ok
            total_mappable += mapped
            total_unmapped += unmapped
            if unmapped > 0:
                problem_leagues.append((league_name, data['country'], unmapped, data['unmapped']))
    
    print(f"\n  ✅ Times já com api_id correto: {total_ok}")
    print(f"  ✓  Times mapeáveis (>60% similaridade): {total_mappable}")
    print(f"  ❌ Times NÃO mapeados: {total_unmapped}")
    print(f"  💰 Créditos consumidos: {total_credits}")
    
    if problem_leagues:
        print(f"\n\n{'='*80}")
        print(f"LIGAS COM TIMES PROBLEMÁTICOS (precisam do dicionário)")
        print(f"{'='*80}")
        for league_name, country, count, unmapped_list in problem_leagues:
            print(f"\n  📋 {league_name} ({country}) - {count} times sem mapeamento:")
            for u in unmapped_list:
                print(f"     '{u['db_name']}' → Mais próximo: '{u['api_name']}' (API ID: {u['api_id']}, Score: {u['score']}%)")

    # Salvar relatório JSON para análise
    with open('/app/mapping_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n\n📄 Relatório JSON salvo em: /app/mapping_report.json")

if __name__ == '__main__':
    main()
