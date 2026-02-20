
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
        
        # 1. Check DB Matches for Feb 2026
        print("\n--- Checking DB Matches ---")
        start_date = datetime.date(2026, 2, 1)
        end_date = datetime.date(2026, 3, 1)
        matches = Match.objects.filter(date__date__range=(start_date, end_date), league__name__icontains="Brasileir", api_id__isnull=True)
        print(f"DB Matches in Feb 2026 (No API ID): {matches.count()}")
        for m in matches[:10]:
            print(f"DB: {m.date} | {m.home_team} vs {m.away_team} | API ID: {m.api_id}")

        # 2. Check Specific Fixture ID from DB (15237894)
        print("\n--- Checking Fixture 15237894 ---")
        url = "https://v3.football.api-sports.io/fixtures"
        params_fix = {"id": 15237894}
        response_fix = requests.get(url, headers=headers, params=params_fix, timeout=10)
        if response_fix.status_code == 200:
            data_fix = response_fix.json().get("response", [])
            if data_fix:
                fx = data_fix[0]
                print(f"Fixture {fx['fixture']['id']}: {fx['fixture']['date']} | {fx['teams']['home']['name']} vs {fx['teams']['away']['name']}")
                print(f"League: {fx['league']['name']} ({fx['league']['id']}) Season: {fx['league']['season']}")
            else:
                print("Fixture not found in API")
        else:
            print("Error checking fixture")
