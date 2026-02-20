
import os
import requests
from django.core.management.base import BaseCommand
import datetime
from matches.models import Match

class Command(BaseCommand):
    help = "Check API Brazil Data"

    def handle(self, *args, **options):
        api_key = "d3b922fd142fb4f2048ada3fb4b3141a"
        headers = {
            "x-rapidapi-host": "v3.football.api-sports.io",
            "x-rapidapi-key": api_key,
        }
        
        # 1. Check DB Matches for April 2026
        print("\n--- Checking DB Matches ---")
        start_date = datetime.date(2026, 4, 1)
        end_date = datetime.date(2026, 5, 1)
        matches = Match.objects.filter(date__date__range=(start_date, end_date), league__name__icontains="Brasileir")
        print(f"DB Matches in April 2026: {matches.count()}")

        # 2. Check API Fixtures for League 71 Season 2026
        print("\n--- Checking API Fixtures for 2026 ---")
        url = "https://v3.football.api-sports.io/fixtures"
        # League 71 = Serie A Brazil
        params_fix = {"league": 71, "season": 2026}
        response_fix = requests.get(url, headers=headers, params=params_fix, timeout=10)
        if response_fix.status_code == 200:
            data_fix = response_fix.json().get("response", [])
            print(f"API Fixtures found for 2026: {len(data_fix)}")
            if data_fix:
                fx = data_fix[0]
                print(f"Example: {fx['fixture']['date']} | {fx['teams']['home']['name']} vs {fx['teams']['away']['name']}")
        else:
            print(f"Error checking API: {response_fix.status_code}")
