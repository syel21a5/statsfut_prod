from django.core.management.base import BaseCommand
from matches.models import Team, League, Match
from matches.utils import TEAM_NAME_MAPPINGS


class Command(BaseCommand):
    help = "Detecta e mescla times duplicados baseado no TEAM_NAME_MAPPINGS"

    def add_arguments(self, parser):
        parser.add_argument(
            "--league_name",
            type=str,
            default=None,
            help="Filtra por liga (opcional). Se omitido, processa todas.",
        )

    def handle(self, *args, **options):
        league_name = options.get("league_name")

        leagues = League.objects.all()
        if league_name:
            leagues = leagues.filter(name=league_name)

        total_fixed = 0

        for league in leagues:
            # Monta mapa inverso: nome_errado -> nome_correto para times desta liga
            teams_in_league = {t.name: t for t in Team.objects.filter(league=league)}

            for wrong_name, correct_name in TEAM_NAME_MAPPINGS.items():
                wrong_team = teams_in_league.get(wrong_name)
                correct_team = teams_in_league.get(correct_name)

                if not wrong_team:
                    continue  # time errado não existe nessa liga, ok

                if not correct_team:
                    # O time correto não existe ainda — apenas renomeia
                    wrong_team.name = correct_name
                    wrong_team.save()
                    teams_in_league[correct_name] = wrong_team
                    del teams_in_league[wrong_name]
                    self.stdout.write(
                        self.style.WARNING(
                            f"[{league.name}] Renomeado: '{wrong_name}' → '{correct_name}'"
                        )
                    )
                    total_fixed += 1
                    continue

                # Ambos existem → mescla: reatribui jogos do errado para o correto
                home_count = Match.objects.filter(
                    league=league, home_team=wrong_team
                ).update(home_team=correct_team)

                away_count = Match.objects.filter(
                    league=league, away_team=wrong_team
                ).update(away_team=correct_team)

                wrong_team.delete()
                del teams_in_league[wrong_name]

                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{league.name}] Mesclado: '{wrong_name}' → '{correct_name}' "
                        f"({home_count} casa, {away_count} fora)"
                    )
                )
                total_fixed += 1

        if total_fixed == 0:
            self.stdout.write(self.style.SUCCESS("Nenhum time duplicado encontrado."))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nTotal de times corrigidos: {total_fixed}")
            )
