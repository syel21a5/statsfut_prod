
from django.core.management.base import BaseCommand
from matches.models import Match, League
from django.db.models import Count

class Command(BaseCommand):
    help = "Force cleanup of duplicate matches (specifically 00:00 vs real time)"

    def handle(self, *args, **options):
        self.stdout.write("Starting Force Cleanup...")
        
        # 1. Get League
        try:
            league = League.objects.get(id=2) # Based on my check output
        except League.DoesNotExist:
            league = League.objects.filter(name__icontains="Brasileir").first()
            
        if not league:
            self.stdout.write(self.style.ERROR("League not found"))
            return

        self.stdout.write(f"Processing League: {league.name} (ID: {league.id})")

        # 2. Find duplicates
        # We look for matches with same date(day), home, away
        matches = Match.objects.filter(league=league).order_by('date')
        
        seen = {}
        deleted = 0
        
        for m in matches:
            if not m.date:
                continue
                
            key = (m.date.date(), m.home_team_id, m.away_team_id)
            
            if key in seen:
                existing = seen[key]
                
                # Check which one to keep
                # Prefer the one with API ID
                # If both have API ID (unlikely for duplicates), prefer non-00:00
                
                keep_existing = False
                
                # Criteria 1: API ID
                if existing.api_id and not m.api_id:
                    keep_existing = True
                elif not existing.api_id and m.api_id:
                    keep_existing = False
                else:
                    # Criteria 2: Time != 00:00
                    existing_hour = existing.date.hour
                    current_hour = m.date.hour
                    
                    if existing_hour != 0 and current_hour == 0:
                        keep_existing = True
                    elif existing_hour == 0 and current_hour != 0:
                        keep_existing = False
                    else:
                        # Tie-breaker: Keep the one with higher ID (newer?) or existing
                        keep_existing = True # Default keep existing
                
                if keep_existing:
                    self.stdout.write(f"  [DUPLICATE] Deleting {m.id} ({m.date} {m.home_team} vs {m.away_team}) - Keeping {existing.id}")
                    m.delete()
                    deleted += 1
                else:
                    self.stdout.write(f"  [DUPLICATE] Deleting {existing.id} ({existing.date} {existing.home_team} vs {existing.away_team}) - Keeping {m.id}")
                    existing.delete()
                    seen[key] = m # Update seen with the kept match
                    deleted += 1
            else:
                seen[key] = m

        self.stdout.write(self.style.SUCCESS(f"Cleanup finished. Deleted {deleted} duplicate matches."))
