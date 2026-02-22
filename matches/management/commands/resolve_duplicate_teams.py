from django.core.management.base import BaseCommand
from django.db import transaction
from matches.models import Team, League, Match, Goal, Player, LeagueStanding, TeamGoalTiming
from matches.utils import TEAM_NAME_MAPPINGS
import sys

class Command(BaseCommand):
    help = "Detecta e mescla times duplicados baseado no TEAM_NAME_MAPPINGS, com tratamento de erros DB/ASCII."

    def add_arguments(self, parser):
        parser.add_argument(
            "--league_name",
            type=str,
            default=None,
            help="Filtra por liga (opcional).",
        )

    def print_safe(self, msg, style_func=None):
        if style_func:
            msg = style_func(msg)
        try:
            self.stdout.write(msg)
        except Exception:
            # Fallback in case of UnicodeEncodeError in CRON environments (LC_ALL=C)
            try:
                msg_ascii = msg.encode('ascii', 'replace').decode('ascii')
                self.stdout.write(msg_ascii)
            except:
                pass

    def handle(self, *args, **options):
        league_name = options.get("league_name")
        leagues = League.objects.all()
        if league_name:
            leagues = leagues.filter(name=league_name)

        total_fixed = 0

        for league in leagues:
            teams_in_league = {t.name: t for t in Team.objects.filter(league=league)}

            for wrong_name, correct_name in TEAM_NAME_MAPPINGS.items():
                wrong_team = teams_in_league.get(wrong_name)
                correct_team = teams_in_league.get(correct_name)

                if not wrong_team:
                    continue  # Time errado nao existe, tudo certo

                try:
                    with transaction.atomic():
                        if not correct_team:
                            # Time correto nao existe: Apenas renomeia o errado
                            wrong_team.name = correct_name
                            wrong_team.save()
                            teams_in_league[correct_name] = wrong_team
                            del teams_in_league[wrong_name]
                            self.print_safe(
                                f"[{league.name}] Renomeado: '{wrong_name}' -> '{correct_name}'", 
                                self.style.WARNING
                            )
                            total_fixed += 1
                            continue

                        # Se ambos existem, mesclar o errado para dentro do correto.
                        
                        # 1. Reatribuir as Partidas (Matches)
                        home_count = Match.objects.filter(league=league, home_team=wrong_team).update(home_team=correct_team)
                        away_count = Match.objects.filter(league=league, away_team=wrong_team).update(away_team=correct_team)
                        
                        # 2. Reatribuir Gols e Jogadores (evitando perda de dados pelo cascade_delete)
                        Goal.objects.filter(team=wrong_team).update(team=correct_team)
                        Player.objects.filter(team=wrong_team).update(team=correct_team)

                        # 3. Remover registros associados que causariam conflitos de UNIQUE (LeagueStanding e TeamGoalTiming)
                        # Como as tabelas vao ser recalculadas no passo 4 do update_all_leagues.sh, n ha problema em deletar.
                        LeagueStanding.objects.filter(team=wrong_team).delete()
                        TeamGoalTiming.objects.filter(team=wrong_team).delete()

                        # 4. Excluir o time duplicado
                        wrong_team.delete()
                        del teams_in_league[wrong_name]

                        self.print_safe(
                            f"[{league.name}] Mesclado com sucesso: '{wrong_name}' -> '{correct_name}' "
                            f"({home_count} jogos H, {away_count} jogos A)", 
                            self.style.SUCCESS
                        )
                        total_fixed += 1
                except Exception as e:
                    import traceback
                    self.print_safe(f"ERRO CRITICO AO MESCLAR {wrong_name} no {league.name}: {e}\n{traceback.format_exc()}", self.style.ERROR)

        if total_fixed == 0:
            self.print_safe("Nenhum time duplicado encontrado.", self.style.SUCCESS)
        else:
            self.print_safe(f"\nTotal de times corrigidos logicamente: {total_fixed}", self.style.SUCCESS)
