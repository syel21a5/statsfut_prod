from django.core.management.base import BaseCommand
from matches.models import League, Team, Match, Season
from django.db.models import Count


class Command(BaseCommand):
    help = (
        "Remove times fantasma/duplicados da liga austríaca. "
        "Usa como 'times canônicos' aqueles que o sofascore gravou (nomes com prefixo SK/FC/TSV/WSG etc.). "
        "Seguro para rodar a qualquer momento — só deleta quem não tem matches."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas lista o que seria feito, sem alterar nada.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN — nenhuma alteração será feita ==="))

        league = League.objects.filter(country='Austria').first()
        if not league:
            self.stdout.write(self.style.ERROR("Liga da Áustria não encontrada no banco."))
            return

        self.stdout.write(f"Liga: {league.name} (ID {league.id})")

        # Mapeamento: nome fantasma → nome canônico (usado pelo sofascore)
        # O sofascore usa nomes completos/oficiais. Os fantasmas são versões curtas
        # criadas pelo import_football_data ou merge_duplicate_teams.
        ghost_to_canonical = {
            # Times-fantasma (versões curtas) → canônico (sofascore)
            'Austria Wien':   'FK Austria Wien',
            'Rapid Wien':     'SK Rapid Wien',
            'Sturm Graz':     'SK Sturm Graz',
            'Tirol':          'WSG Tirol',
            'Altach':         'SC Rheindorf Altach',
            'Grazer AK':      'Grazer AK 1902',
            'Ried':           'SV Ried',
            'Salzburg':       'Red Bull Salzburg',
            'BW Linz':        'FC Blau-Weiß Linz',
            'Blau-Weiss Linz':'FC Blau-Weiß Linz',
            'LASK Linz':      'LASK',
            'Hartberg':       'TSV Hartberg',
            'Austria Klagenfurt': 'SK Austria Klagenfurt',
            'Austria Lustenau':   'SC Austria Lustenau',
            'Wolfsberger AC': 'Wolfsberger AC',  # self-map, será ignorado
            # Nomes com erros de parsing (SoccerStats)
            'a.e.t. (1-1, 0-0)  Austria Lustenau': None,
            'Austria Wien            v FC Admira Wacker': None,
        }

        merged = 0
        deleted = 0

        for ghost_name, canonical_name in ghost_to_canonical.items():
            ghost_team = Team.objects.filter(name=ghost_name, league=league).first()
            if not ghost_team:
                continue

            # Contar jogos do ghost
            ghost_home = Match.objects.filter(home_team=ghost_team).count()
            ghost_away = Match.objects.filter(away_team=ghost_team).count()
            ghost_total = ghost_home + ghost_away

            if canonical_name is None:
                # Time com nome inválido de parsing — delete direto se sem jogos
                if ghost_total == 0:
                    self.stdout.write(self.style.WARNING(
                        f"[DELETE] Time inválido '{ghost_name}' (0 jogos)"
                    ))
                    if not dry_run:
                        ghost_team.delete()
                    deleted += 1
                else:
                    self.stdout.write(self.style.ERROR(
                        f"[SKIP] Time inválido '{ghost_name}' tem {ghost_total} jogos — não deleta automaticamente!"
                    ))
                continue

            if ghost_name == canonical_name:
                continue  # self-map, ignora

            canonical_team = Team.objects.filter(name=canonical_name, league=league).first()

            if canonical_team and ghost_team.id != canonical_team.id:
                # Ambos existem → redireciona jogos do ghost para o canônico
                self.stdout.write(
                    f"[MERGE] '{ghost_name}' ({ghost_total} jogos) → '{canonical_name}'"
                )
                if not dry_run:
                    Match.objects.filter(home_team=ghost_team).update(home_team=canonical_team)
                    Match.objects.filter(away_team=ghost_team).update(away_team=canonical_team)
                    ghost_team.delete()
                merged += 1

            elif not canonical_team and ghost_total > 0:
                # Canônico não existe, ghost tem jogos → renomeia para o nome canônico
                self.stdout.write(
                    f"[RENAME] '{ghost_name}' ({ghost_total} jogos) → '{canonical_name}'"
                )
                if not dry_run:
                    ghost_team.name = canonical_name
                    ghost_team.save()
                merged += 1

            elif ghost_total == 0:
                # Ghost sem jogos → simplesmente deleta
                self.stdout.write(self.style.WARNING(
                    f"[DELETE] '{ghost_name}' (0 jogos, sem canônico)"
                ))
                if not dry_run:
                    ghost_team.delete()
                deleted += 1

        # Também limpa Season duplicatas (seguro — só remappa os matches)
        dup_years = Season.objects.values('year').annotate(c=Count('id')).filter(c__gt=1)
        for entry in dup_years:
            year = entry['year']
            seasons = list(Season.objects.filter(year=year).order_by('id'))
            primary = seasons[0]
            for extra in seasons[1:]:
                count = Match.objects.filter(season=extra).count()
                self.stdout.write(f"[SEASON] Merge Season {year} ID {extra.id} → {primary.id} ({count} matches)")
                if not dry_run:
                    Match.objects.filter(season=extra).update(season=primary)
                    extra.delete()

        action = "Simulação" if dry_run else "Limpeza"
        self.stdout.write(self.style.SUCCESS(
            f"\n{action} concluída: {merged} times mergeados/renomeados, {deleted} deletados."
        ))
