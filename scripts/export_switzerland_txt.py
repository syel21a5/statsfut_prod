import os
import sys
import django  # type: ignore
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Match, Season  # type: ignore
from django.db.models import Q  # type: ignore

def export_switzerland():
    league = League.objects.get(id=42)
    base_dir = os.path.join('historical_data', 'Switzerland', 'Super League')
    os.makedirs(base_dir, exist_ok=True)

    seasons = Season.objects.all().order_by('year')

    for season in seasons:
        matches = Match.objects.filter(
            league=league,
            season=season,
            status__in=['Finished', 'FT', 'AET', 'PEN', 'FINISHED']
        ).order_by('date')

        if not matches.exists():
            continue

        # Format: 2023-24_sw1.txt
        # If year=2024, it's 2023-24. If year=2023, it's 2022-23.
        # SofaScore seasonal leagues often use year as the end year or start year.
        # For Switzerland, let's use YY-YY format. 
        # Sofa ID 77152 (2025/26) -> year 2026? 
        # I'll check how Season year is stored.
        
        y_end = season.year
        y_start = y_end - 1
        filename = f"{y_start}-{y_end % 100:02d}_sw1.txt"
        file_path = os.path.join(base_dir, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            for m in matches:
                date_str = m.date.strftime('%d/%m/%Y') if m.date else '00/00/0000'
                line = f"{date_str},{m.home_team.name},{m.away_team.name},{m.home_score},{m.away_score}\n"
                f.write(line)
        
        print(f"✅ Exportado: {file_path}")

if __name__ == "__main__":
    export_switzerland()
