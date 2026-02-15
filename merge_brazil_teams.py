
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, League, LeagueStanding

def merge_teams(league_name, canonical_name, duplicate_names):
    league = League.objects.get(name=league_name)
    canonical_team, created = Team.objects.get_or_create(name=canonical_name, league=league)
    if created:
        print(f"Created canonical team: {canonical_name}")

    for dup_name in duplicate_names:
        try:
            dup_team = Team.objects.get(name=dup_name, league=league)
            if dup_team.id == canonical_team.id:
                print(f"Skipping {dup_name} (ID:{dup_team.id}) as it is the same as canonical.")
                continue
            print(f"Merging {dup_name} (ID:{dup_team.id}) into {canonical_name} (ID:{canonical_team.id})...")
            
            # Update matches
            Match.objects.filter(home_team=dup_team).update(home_team=canonical_team)
            Match.objects.filter(away_team=dup_team).update(away_team=canonical_team)
            
            # Delete dup team (CASCADE will handle standings if they exist, 
            # but we explicitly cleared them in previous version, let's just delete team)
            dup_team.delete()
        except Team.DoesNotExist:
            continue
        except Exception as e:
            print(f"Error merging {dup_name}: {e}")

if __name__ == "__main__":
    merges = [
        ('Brasileirão', 'CA Paranaense', ['Athletico PR', 'Athletico-PR', 'Atletico PR']),
        ('Brasileirão', 'CA Mineiro', ['Atletico MG', 'Atletico-MG', 'Atlético Mineiro', 'Atlético-MG']),
        ('Brasileirão', 'Corinthians', ['SC Corinthians Paulista', 'Sport Club Corinthians Paulista']),
        ('Brasileirão', 'Flamengo', ['Flamengo RJ', 'CR Flamengo']),
        ('Brasileirão', 'Vasco', ['Vasco da Gama', 'CR Vasco da Gama']),
        ('Brasileirão', 'Vitoria', ['EC Vitória', 'Vitoria BA']),
        ('Brasileirão', 'Botafogo', ['Botafogo FR', 'Botafogo RJ']),
        ('Brasileirão', 'RB Bragantino', ['Bragantino', 'Red Bull Bragantino']),
        ('Brasileirão', 'Chapecoense AF', ['Chapecoense', 'Chapecoense-SC']),
        ('Brasileirão', 'Coritiba FBC', ['Coritiba']),
        ('Brasileirão', 'Internacional', ['SC Internacional']),
        ('Brasileirão', 'Fluminense', ['Fluminense FC']),
        ('Brasileirão', 'Sao Paulo', ['São Paulo', 'São Paulo FC']),
        ('Brasileirão', 'Cruzeiro', ['Cruzeiro EC']),
        ('Brasileirão', 'Mirassol FC', ['Mirassol']),
        ('Brasileirão', 'Clube do Remo', ['Remo']),
        ('Brasileirão', 'Palmeiras', ['SE Palmeiras']),
        ('Brasileirão', 'Goias', ['Goias EC']),
        ('Brasileirão', 'Cuiaba', ['Cuiaba EC']),
        ('Brasileirão', 'Fortaleza', ['Fortaleza EC']),
        ('Brasileirão', 'America MG', ['America-MG']),
        ('Brasileirão', 'Atletico GO', ['Atletico-GO']),
        ('Brasileirão', 'Juventude', ['EC Juventude']),
    ]
    
    for league_name, canonical, dups in merges:
        merge_teams(league_name, canonical, dups)
    
    print("Merge complete.")
