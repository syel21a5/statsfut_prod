from django.core.management.base import BaseCommand
from django.utils import timezone
from matches.models import League, Team, Match, Season
import requests
from bs4 import BeautifulSoup
from io import StringIO
import csv
from datetime import datetime
import re
from collections import defaultdict


class Command(BaseCommand):
    help = "Importa jogos da Argentina (Primera Division) do football-data.co.uk (a partir de um ano)"

    def add_arguments(self, parser):
        parser.add_argument('--from_year', type=int, default=2016, help='Ano inicial para importar (inclusive)')
        parser.add_argument('--to_year', type=int, default=None, help='Ano final para importar (inclusive). Padrão: ano atual')
        parser.add_argument('--dry_run', action='store_true', help='Não grava no banco, apenas relata')

    def handle(self, *args, **kwargs):
        from_year = kwargs['from_year']
        to_year = kwargs['to_year'] or timezone.now().year
        dry_run = kwargs['dry_run']

        base_url = "https://www.football-data.co.uk/argentina.php"
        self.stdout.write(self.style.SUCCESS(f"Baixando índice: {base_url}"))
        r = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        csv_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith('.csv'):
                if href.startswith('//'):
                    url = 'https:' + href
                elif href.startswith('http'):
                    url = href
                else:
                    url = requests.compat.urljoin(base_url, href)
                year_match = re.search(r'/mmz\d+/(\\d{2})(\\d{2})/', url)
                start_year = None
                if year_match:
                    y1 = int(year_match.group(1))
                    start_year = 2000 + y1
                csv_links.append((url, start_year))

        csv_links = [(url, yr) for (url, yr) in csv_links if (yr is None or yr >= from_year)]

        guess_urls = []
        for y in range(from_year, to_year + 1):
            y1 = str(y % 100).zfill(2)
            y2 = str((y + 1) % 100).zfill(2)
            guess_urls.append((f"https://www.football-data.co.uk/mmz4281/{y1}{y2}/ARG.csv", y))
        guess_urls.append(("https://www.football-data.co.uk/new/ARG.csv", None))

        seen = set()
        for u in guess_urls + csv_links:
            if u[0] not in seen:
                seen.add(u[0])
                csv_links.append(u)

        if not csv_links:
            self.stdout.write(self.style.WARNING("Nenhum CSV encontrado na página."))
            return

        league_obj, _ = League.objects.get_or_create(name="Primera Division", country="Argentina")

        created = 0
        updated = 0
        skipped = 0
        files_processed = 0
        per_year = defaultdict(int)

        def parse_date(val: str):
            val = (val or '').strip()
            for fmt in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(val, fmt)
                except Exception:
                    continue
            # Algumas planilhas usam formato texto tipo 'DD/MM/YY HH:MM:SS'
            try:
                base = val.split()[0]
                return datetime.strptime(base, "%d/%m/%y")
            except Exception:
                return None

        for url, start_year in csv_links:
            self.stdout.write(f"Processando CSV: {url}")
            try:
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                if resp.status_code != 200:
                    self.stdout.write(self.style.WARNING(f"Falha ao baixar: {url} [{resp.status_code}]"))
                    continue
                content = resp.content.decode('utf-8', errors='ignore')
                f = StringIO(content)
                reader = csv.DictReader(f)
                row_count = 0
                for row in reader:
                    row_count += 1
                    date_s = row.get('Date') or row.get('date')
                    ht = (row.get('HomeTeam') or row.get('Home') or '').strip()
                    at = (row.get('AwayTeam') or row.get('Away') or '').strip()
                    fthg = row.get('FTHG') or row.get('HG') or ''
                    ftag = row.get('FTAG') or row.get('AG') or ''

                    if not (date_s and ht and at):
                        skipped += 1
                        continue

                    dt = parse_date(date_s)
                    if not dt:
                        skipped += 1
                        continue

                    if dt.year < from_year or dt.year > to_year:
                        continue

                    season_obj, _ = Season.objects.get_or_create(year=dt.year)

                    try:
                        h_score = int(fthg) if fthg != '' else None
                        a_score = int(ftag) if ftag != '' else None
                    except Exception:
                        h_score = None
                        a_score = None

                    if dry_run:
                        continue

                    home_team, _ = Team.objects.get_or_create(name=ht, league=league_obj)
                    away_team, _ = Team.objects.get_or_create(name=at, league=league_obj)
                    if home_team == away_team:
                        skipped += 1
                        continue

                    defaults = {
                        'date': timezone.make_aware(dt) if timezone.is_naive(dt) else dt,
                        'home_score': h_score,
                        'away_score': a_score,
                        'status': 'Finished' if (h_score is not None and a_score is not None) else 'Scheduled'
                    }
                    per_year[dt.year] += 1
                    obj, was_created = Match.objects.update_or_create(
                        league=league_obj,
                        season=season_obj,
                        home_team=home_team,
                        away_team=away_team,
                        date=defaults['date'],
                        defaults=defaults
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

                files_processed += 1
                self.stdout.write(self.style.SUCCESS(f"✓ {url} - linhas: {row_count}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao processar {url}: {e}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run concluído (nenhum dado gravado)."))
        self.stdout.write(self.style.SUCCESS(f"Concluído. Arquivos: {files_processed}, Criados: {created}, Atualizados: {updated}, Ignorados: {skipped}"))
        if per_year:
            self.stdout.write("Por ano:")
            for y in sorted(per_year.keys()):
                self.stdout.write(f"{y}: {per_year[y]}")
