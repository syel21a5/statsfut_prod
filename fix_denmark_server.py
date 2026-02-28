import os
import django
import sys
from collections import Counter
from django.db.models import Count

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import Team, Match, LeagueStanding, League, Season

def fix_denmark_server():
    print("=== INICIANDO CORREÇÃO SUPERLIGA DINAMARCA (SERVIDOR) ===")
    
    try:
        league = League.objects.get(name='Superliga', country='Dinamarca')
        print(f"Liga Encontrada: {league} (ID: {league.id})")
        
        # 1. MERGE TEAMS
        print("\n--- 1. Unificando Times Duplicados ---")
        # Map: Old Name -> New Name
        mapping = {
            'Aarhus': 'AGF Aarhus',
            'Brondby': 'Brondby IF',
            'FC Copenhagen': 'FC Kobenhavn',
            'Midtjylland': 'FC Midtjylland',
            'Odense': 'Odense BK',
            'Vejle': 'Vejle BK'
        }
        
        all_teams = {t.name: t for t in Team.objects.filter(league=league)}
        
        for old_name, new_name in mapping.items():
            if old_name not in all_teams or new_name not in all_teams:
                continue
                
            old_team = all_teams[old_name]
            new_team = all_teams[new_name]
            
            print(f"Merging '{old_team.name}' (ID {old_team.id}) -> '{new_team.name}' (ID {new_team.id})...")
            
            # Update Matches
            Match.objects.filter(home_team=old_team).update(home_team=new_team)
            Match.objects.filter(away_team=old_team).update(away_team=new_team)
            
            # Handle Standings
            for standing in LeagueStanding.objects.filter(team=old_team):
                if not LeagueStanding.objects.filter(team=new_team, season=standing.season, league=standing.league).exists():
                    standing.team = new_team
                    standing.save()
                else:
                    standing.delete() # Duplicate standing
            
            # Delete Old Team
            old_team.delete()
            print(f"  OK: '{old_name}' merged and deleted.")

        # 2. CLEANUP DUPLICATES
        print("\n--- 2. Removendo Jogos Duplicados ---")
        all_matches = Match.objects.filter(league=league)
        # Signature: Date (Day) + Home + Away
        # Using normalized date string
        
        # We need to be careful with timestamps. Just check YYYY-MM-DD
        sigs = {} # Sig -> List of Match IDs
        
        for m in all_matches:
            d_str = m.date.strftime('%Y-%m-%d') if m.date else "NoDate"
            sig = (d_str, m.home_team_id, m.away_team_id)
            if sig not in sigs:
                sigs[sig] = []
            sigs[sig].append(m.id)
            
        duplicates_count = 0
        deleted_count = 0
        
        for sig, ids in sigs.items():
            if len(ids) > 1:
                duplicates_count += 1
                # Sort IDs to keep the oldest (lowest ID) or newest?
                # Usually keep the one with most info? Assuming they are identical copies.
                # Let's keep the lowest ID (created first)
                ids.sort()
                keep_id = ids[0]
                delete_ids = ids[1:]
                
                Match.objects.filter(id__in=delete_ids).delete()
                deleted_count += len(delete_ids)
                
        print(f"Encontrados {duplicates_count} jogos duplicados.")
        print(f"Deletados {deleted_count} registros excedentes.")

        # 3. VERIFICATION
        print("\n--- 3. Verificação Final (Temporada 2026) ---")
        matches_2026 = Match.objects.filter(league=league, season__year=2026)
        total = matches_2026.count()
        may_matches = matches_2026.filter(date__month=5).count()
        
        print(f"Total de jogos 2026: {total}")
        if may_matches > 0:
            print(f"ALERTA: Ainda existem {may_matches} jogos em Maio na temporada 2026!")
        else:
            print("OK: Nenhum jogo em Maio na temporada 2026.")
            
        print("\n--- CONCLUÍDO ---")

    except League.DoesNotExist:
        print("Liga 'Superliga' não encontrada.")
    except Exception as e:
        print(f"Erro Crítico: {e}")

if __name__ == "__main__":
    fix_denmark_server()
