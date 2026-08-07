import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, League

def clean_database():
    # Helper list of valid PL teams (partial list to catch obvious outliers)
    # Actually, easier to just delete the specific teams the user complained about
    # and any others that seem out of place.
    
    # Or strict filter: Keep only teams that are actually in the Premier League.
    # Since I don't have a definitive list handy in code, I'll delete the ones I saw in the log.
    
    bad_teams = [
        "Santos FC", "Fluminense FC", "SC Internacional", "Botafogo FR", 
        "EC Vitória", "Chapecoense AF", "Mirassol FC", "RB Bragantino", 
        "Clube do Remo", "Cruzeiro EC", "Grêmio FBPA", "Coritiba FBC", "São Paulo FC"
    ]
    
    print("Cleaning database of incorrect teams...")
    
    deleted_count = 0
    for name in bad_teams:
        try:
            teams = Team.objects.filter(name=name)
            for t in teams:
                # Delete matches involving this team first (cascade usually handles this, but let's be safe)
                # Match.objects.filter(models.Q(home_team=t) | models.Q(away_team=t)).delete()
                # Cascade delete the team
                t.delete()
                print(f"Deleted team: {name}")
                deleted_count += 1
        except Exception as e:
            print(f"Error deleting {name}: {e}")
            
    print(f"Done. Deleted {deleted_count} teams.")

if __name__ == '__main__':
    clean_database()
