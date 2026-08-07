
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
        ('Brasileirão', 'Gremio', ['Grêmio FBPA']),
        ('Brasileirão', 'Botafogo', ['Botafogo FR', 'Botafogo RJ']),
        ('Brasileirão', 'CA Paranaense', ['Athletico PR', 'Athletico-PR', 'Atletico PR', 'CA Paranaense']),
        ('Brasileirão', 'CA Mineiro', ['Atletico MG', 'Atletico-MG', 'Atlético Mineiro', 'Atlético-MG', 'CA Mineiro']),
        ('Brasileirão', 'RB Bragantino', ['Bragantino', 'Red Bull Bragantino']),
        ('Brasileirão', 'Corinthians', ['SC Corinthians Paulista', 'Sport Club Corinthians Paulista', 'Corinthians']),
        ('Brasileirão', 'Flamengo', ['Flamengo RJ', 'CR Flamengo', 'Flamengo']),
        ('Brasileirão', 'Vasco', ['Vasco da Gama', 'CR Vasco da Gama', 'Vasco']),
        ('Brasileirão', 'Vitoria', ['EC Vitória', 'Vitoria BA', 'Vitoria']),
        ('Brasileirão', 'Chapecoense AF', ['Chapecoense', 'Chapecoense-SC', 'Chapecoense AF']),
        ('Brasileirão', 'Coritiba FBC', ['Coritiba', 'Coritiba FBC']),
        ('Brasileirão', 'Internacional', ['SC Internacional', 'Internacional']),
        ('Brasileirão', 'Fluminense', ['Fluminense FC', 'Fluminense']),
        ('Brasileirão', 'Sao Paulo', ['São Paulo', 'São Paulo FC', 'Sao Paulo']),
        ('Brasileirão', 'Cruzeiro', ['Cruzeiro EC', 'Cruzeiro']),
        ('Brasileirão', 'Mirassol FC', ['Mirassol', 'Mirassol FC']),
        ('Brasileirão', 'Clube do Remo', ['Remo', 'Clube do Remo']),
        ('Brasileirão', 'Palmeiras', ['SE Palmeiras', 'Palmeiras']),
        ('Brasileirão', 'Goias', ['Goias EC', 'Goias']),
        ('Brasileirão', 'Cuiaba', ['Cuiaba EC', 'Cuiaba']),
        ('Brasileirão', 'Fortaleza', ['Fortaleza EC', 'Fortaleza']),
        ('Brasileirão', 'America MG', ['America-MG', 'America MG']),
        ('Brasileirão', 'Atletico GO', ['Atletico-GO', 'Atletico GO']),
        ('Brasileirão', 'Juventude', ['EC Juventude', 'Juventude']),
    ]
    
    for league_name, canonical, dups in merges:
        merge_teams(league_name, canonical, dups)
    
    print("Merge complete.")
