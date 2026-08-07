import os
import sys
import django
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Match, Season

def get_day_of_week_pt(dt):
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return days[dt.weekday()]

def get_month_abbr(dt):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return months[dt.month - 1]

def export_to_statsfut_txt(league_name, country, year):
    season_str = f"{year-1}/{str(year)[2:]}"
    league = League.objects.filter(name=league_name, country=country).first()
    if not league:
        print(f"Liga não encontrada: {league_name} ({country})")
        return

    matches = Match.objects.filter(league=league, season__year=year).order_by('date')
    if not matches.exists():
        print(f"Sem jogos para {league_name} {year}")
        return

    # Info gathering
    teams_count = matches.values('home_team').distinct().count()
    matches_count = matches.count()
    start_date = matches.first().date
    end_date = matches.last().date
    diff_days = (end_date - start_date).days

    filename = f"{year-1}-{str(year)[2:]}_fr1.txt"
    filepath = os.path.join("historical_data", "France", "Ligue 1", filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"= {country} | {league_name} {season_str}\n\n")
        f.write(f"# Date       {get_day_of_week_pt(start_date)} {get_month_abbr(start_date)}/{start_date.day} {start_date.year} - {get_day_of_week_pt(end_date)} {get_month_abbr(end_date)}/{end_date.day} {end_date.year} ({diff_days}d)\n")
        f.write(f"# Teams      {teams_count}\n")
        f.write(f"# Matches    {matches_count}\n")
        f.write(f"# Stages     Regular Season ({matches_count})\n\n\n\n")

        # Group by matchday if available, or just by date
        # Since football-data doesn't always have Matchday, we group by month/day
        current_date = None
        for m in matches:
            m_date = m.date
            if m_date.date() != current_date:
                current_date = m_date.date()
                f.write(f"\n» {get_day_of_week_pt(m_date)} {get_month_abbr(m_date)}/{m_date.day}\n")
            
            time_str = m_date.strftime("%H.%M")
            home = m.home_team.name.ljust(25)
            away = m.away_team.name.ljust(25)
            score = f"{m.home_score}-{m.away_score}"
            
            f.write(f"    {time_str}  {home} v {away} {score}\n")

    print(f"✅ Exportado: {filepath}")

if __name__ == "__main__":
    years = range(2016, 2026) # 2016 to 2025
    for y in years:
        export_to_statsfut_txt("Ligue 1", "Franca", y)
