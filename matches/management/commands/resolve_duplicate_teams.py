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
            try:
                msg_ascii = msg.encode('ascii', 'replace').decode('ascii')
                self.stdout.write(msg_ascii)
            except:
                pass

    def _merge_teams(self, wrong_team, correct_team, league):
        """Mescla o wrong_team para o correct_team dentro de uma liga."""
        with transaction.atomic():
            # 1. Reatribuir as Partidas (Matches)
            home_count = Match.objects.filter(league=league, home_team=wrong_team).update(home_team=correct_team)
            away_count = Match.objects.filter(league=league, away_team=wrong_team).update(away_team=correct_team)
            
            # 2. Reatribuir Gols e Jogadores
            Goal.objects.filter(team=wrong_team).update(team=correct_team)
            Player.objects.filter(team=wrong_team).update(team=correct_team)

            # 3. Remover registros associados que causariam conflitos de UNIQUE
            LeagueStanding.objects.filter(team=wrong_team).delete()
            TeamGoalTiming.objects.filter(team=wrong_team).delete()

            # 4. Excluir o time duplicado
            wrong_team.delete()
            return home_count, away_count

    def handle(self, *args, **options):
        league_name = options.get("league_name")
        leagues = League.objects.all()
        if league_name:
            leagues = leagues.filter(name=league_name)

        total_fixed = 0

        self.print_safe(f"Iniciando resolução de duplicatas. Mapeamentos carregados: {len(TEAM_NAME_MAPPINGS)}", self.style.SUCCESS)

        for league in leagues:
            self.print_safe(f"Processando liga: {league.name} ({league.country})")
            
            # Dicionário usando o nome LIMPO (.strip()) para a busca
            teams_in_league = {}
            # Precisamos processar os times em ordem estável (pelo ID)
            all_teams = list(Team.objects.filter(league=league).order_by('id'))
            self.print_safe(f"  Encontrados {len(all_teams)} times na liga.")
            
            for t in all_teams:
                name_clean = t.name.strip()
                
                if name_clean in teams_in_league and teams_in_league[name_clean].id != t.id:
                    # AUTO-MERGE: "Leeds" e "Leeds "
                    self.print_safe(f"[{league.name}] AUTO-MERGE WHITESPACE: '{t.name}' -> '{teams_in_league[name_clean].name}'", self.style.WARNING)
                    try:
                        self._merge_teams(t, teams_in_league[name_clean], league)
                        total_fixed += 1
                    except Exception as e:
                        self.print_safe(f"Erro no auto-merge: {e}", self.style.ERROR)
                else:
                    teams_in_league[name_clean] = t

            # Processar mapeamentos oficiais
            for wrong_name, correct_name in TEAM_NAME_MAPPINGS.items():
                wrong_team = teams_in_league.get(wrong_name.strip())
                correct_team = teams_in_league.get(correct_name.strip())

                if not wrong_team or (correct_team and wrong_team.id == correct_team.id):
                    continue

                try:
                    if not correct_team:
                        # Apenas renomeia
                        old_name = wrong_team.name
                        wrong_team.name = correct_name
                        wrong_team.save()
                        teams_in_league[correct_name.strip()] = wrong_team
                        self.print_safe(f"[{league.name}] Renomeado: '{old_name}' -> '{correct_name}'", self.style.WARNING)
                        total_fixed += 1
                    else:
                        # Mescla
                        h, a = self._merge_teams(wrong_team, correct_team, league)
                        # Remove do dict de busca
                        for k, v in list(teams_in_league.items()):
                            if v.id == wrong_team.id:
                                del teams_in_league[k]
                        
                        self.print_safe(f"[{league.name}] Mesclado: '{wrong_team.name}' -> '{correct_team.name}' ({h+a} jogos)", self.style.SUCCESS)
                        total_fixed += 1
                except Exception as e:
                    self.print_safe(f"Erro ao mesclar {wrong_name}: {e}", self.style.ERROR)

        self.print_safe(f"\nConcluido. Total de correcoes: {total_fixed}", self.style.SUCCESS)
