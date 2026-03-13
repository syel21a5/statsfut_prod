import os
import sys
import django
import argparse
from django.utils.text import slugify

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Match

def get_day_of_week_en(dt):
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return days[dt.weekday()]

def get_month_abbr(dt):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return months[dt.month - 1]

def compute_season_label(matches, season_year):
    if not matches:
        return str(season_year)
    start_year = matches[0].date.year if matches[0].date else None
    end_year = matches[-1].date.year if matches[-1].date else None
    if start_year and end_year and start_year != end_year:
        return f"{season_year-1}-{str(season_year)[2:]}"
    return str(season_year)

def export_to_statsfut_txt(league_name, country, year, output_country_dir=None, output_league_dir=None, file_suffix=None):
    league = League.objects.filter(name=league_name, country=country).first()
    if not league:
        print(f"[DEBUG] Liga não encontrada: {league_name} ({country})")
        return

    matches = Match.objects.filter(league=league, season__year=year).order_by('date')
    if not matches.exists():
        print(f"Sem jogos para {league_name} {year}")
        return
    
    matches_list = list(matches)
    season_label = compute_season_label(matches_list, year)

    # Info gathering
    teams_count = matches.values('home_team').distinct().count()
    matches_count = matches.count()
    start_date = matches.first().date
    end_date = matches.last().date
    diff_days = (end_date - start_date).days

    out_country = output_country_dir if output_country_dir is not None else country
    out_league = output_league_dir if output_league_dir is not None else league_name
    suffix = file_suffix if file_suffix is not None else slugify(league_name)
    filename = f"{season_label}_{suffix}.txt"
    filepath = os.path.join("historical_data", out_country, out_league, filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"= {country} | {league_name} {season_label}\n\n")
        f.write(f"# Date       {get_day_of_week_en(start_date)} {get_month_abbr(start_date)}/{start_date.day} {start_date.year} - {get_day_of_week_en(end_date)} {get_month_abbr(end_date)}/{end_date.day} {end_date.year} ({diff_days}d)\n")
        f.write(f"# Teams      {teams_count}\n")
        f.write(f"# Matches    {matches_count}\n")
        f.write(f"# Stages     Regular Season ({matches_count})\n\n\n\n")

        current_date = None
        for m in matches_list:
            m_date = m.date
            if m_date.date() != current_date:
                current_date = m_date.date()
                f.write(f"\n» {get_day_of_week_en(m_date)} {get_month_abbr(m_date)}/{m_date.day}\n")
            
            time_str = m_date.strftime("%H.%M")
            home = m.home_team.name.ljust(25)
            away = m.away_team.name.ljust(25)
            score = f"{m.home_score}-{m.away_score}"
            
            f.write(f"    {time_str}  {home} v {away} {score}\n")

    print(f"✅ Exportado: {filepath}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--league_name", default="Brasileirao")
    parser.add_argument("--country", default="Brasil")
    parser.add_argument("--start_year", type=int, default=2016)
    parser.add_argument("--end_year", type=int, default=2025)
    parser.add_argument("--output_country_dir", default=None)
    parser.add_argument("--output_league_dir", default=None)
    parser.add_argument("--file_suffix", default="br1")
    args = parser.parse_args()

    for y in range(args.start_year, args.end_year + 1):
        export_to_statsfut_txt(
            args.league_name,
            args.country,
            y,
            output_country_dir=args.output_country_dir,
            output_league_dir=args.output_league_dir,
            file_suffix=args.file_suffix,
        )
