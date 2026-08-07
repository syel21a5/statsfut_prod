from django.core.management.base import BaseCommand
from matches.models import League, Match, Goal
from django.db.models import Q
from django.utils import timezone
import unicodedata
import re



FINISHED_STATUSES = ['Finished', 'FT', 'AET', 'PEN', 'FINISHED']


def normalize_name(name):
    """Normaliza nome do time para comparação: lowercase, sem acentos, sem espaços extras."""
    if not name:
        return ''
    # Remove acentos
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase, remove espaços extras
    ascii_name = re.sub(r'\s+', ' ', ascii_name.strip().lower())
    return ascii_name


class Command(BaseCommand):
    help = "Remove partidas duplicadas de uma liga. Detecta duplicatas pelo NOME dos times (normalizado) no mesmo dia do calendário."

    def add_arguments(self, parser):
        parser.add_argument(
            '--league_name', type=str, default=None,
            help='Nome da liga para filtrar (ex: "Brasileirao"). Se omitido, verifica TODAS as ligas.'
        )
        parser.add_argument(
            '--country', type=str, default=None,
            help='País da liga para filtrar (ex: "Brasil").'
        )
        parser.add_argument(
            '--dry_run', action='store_true', default=False,
            help='Apenas exibe os duplicados sem deletar nada.'
        )

    def _merge_match_data(self, keeper, duplicate):
        """
        Mescla dados do duplicado para o keeper.
        Prioridade: keeper mantém seus dados; campos que estão None no keeper são preenchidos pelo duplicate.
        Gols vinculados ao duplicate são movidos para o keeper.
        """
        # Campos de estatísticas para mesclar
        stat_fields = [
            'home_score', 'away_score', 'ht_home_score', 'ht_away_score',
            'home_corners', 'away_corners', 'home_yellow', 'away_yellow',
            'home_red', 'away_red', 'home_shots', 'away_shots',
            'home_shots_on_target', 'away_shots_on_target',
            'home_fouls', 'away_fouls', 'elapsed_time',
            'home_team_win_odds', 'draw_odds', 'away_team_win_odds',
            'statistics_data', 'predictions_data', 'h2h_data',
        ]
        
        changed = False
        for field in stat_fields:
            keeper_val = getattr(keeper, field, None)
            dup_val = getattr(duplicate, field, None)
            if keeper_val is None and dup_val is not None:
                setattr(keeper, field, dup_val)
                changed = True
        
        # Mescla status: preferir FT/AET/PEN se o keeper ainda está como Scheduled
        if keeper.status not in FINISHED_STATUSES and duplicate.status in FINISHED_STATUSES:
            keeper.status = duplicate.status
            changed = True
        
        # Mescla api_id: se o keeper não tem, pega do duplicado
        if not keeper.api_id and duplicate.api_id:
            keeper.api_id = duplicate.api_id
            # Remove o api_id do duplicado para evitar erro de unicidade ao salvar o keeper
            duplicate.api_id = None
            duplicate.save()
            changed = True
        
        # Mescla round_name: se o keeper não tem, pega do duplicado
        if not keeper.round_name and duplicate.round_name:
            keeper.round_name = duplicate.round_name
            changed = True
        
        if changed:
            keeper.save()
        
        # Move gols do duplicado para o keeper
        goals_moved = 0
        for goal in duplicate.goals.all():
            # Verifica se já existe um gol equivalente no keeper (mesmo jogador e minuto)
            exists = keeper.goals.filter(
                player_name=goal.player_name,
                minute=goal.minute
            ).exists()
            if not exists:
                goal.match = keeper
                goal.save()
                goals_moved += 1
        
        # Move ticket_selections se houver
        try:
            for sel in duplicate.ticket_selections.all():
                sel.match = keeper
                sel.save()
        except Exception:
            pass  # ticket_selections pode não existir
        
        return changed, goals_moved

    def handle(self, *args, **options):
        league_name = options.get('league_name')
        country = options.get('country')
        dry_run = options.get('dry_run')

        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  MODO DRY RUN: Nenhum registro será deletado."))

        # Seleciona as ligas
        if league_name:
            qs = League.objects.all()
            if country:
                qs = qs.filter(name__iexact=league_name, country__iexact=country)
            else:
                qs = qs.filter(name__iexact=league_name)
            leagues = list(qs)
        else:
            leagues = list(League.objects.all())

        if not leagues:
            self.stdout.write(self.style.ERROR("Nenhuma liga encontrada com os filtros fornecidos."))
            return

        total_deleted = 0

        for league in leagues:
            self.stdout.write(f"\n📋 Verificando: {league.name} ({league.country}) - ID: {league.id}")

            matches = Match.objects.filter(league=league).select_related(
                'home_team', 'away_team', 'season'
            ).order_by('date', 'id')

            # Agrupa por (data_calendario, nome_home_normalizado, nome_away_normalizado)
            # Usa NOMES em vez de IDs para detectar cross-league duplicates
            seen = {}
            for match in matches:
                if not match.date or not match.home_team or not match.away_team:
                    continue
                # Usa apenas a data do calendário local, ignora horário
                day_key = timezone.localtime(match.date).date()
                home_norm = normalize_name(match.home_team.name)
                away_norm = normalize_name(match.away_team.name)
                key = (day_key, home_norm, away_norm)

                if key not in seen:
                    seen[key] = []
                seen[key].append(match)

            league_deleted = 0
            for key, match_list in seen.items():
                if len(match_list) <= 1:
                    continue

                home_name = match_list[0].home_team.name
                away_name = match_list[0].away_team.name
                date_str = key[0].strftime('%d/%m/%Y')

                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠️  Duplicata ({len(match_list)}x): {home_name} vs {away_name} em {date_str}"
                    )
                )

                # Estratégia de escolha do "keeper":
                # 1. Prefere o que tem o time pertencente à MESMA LIGA
                # 2. Depois, prefere api_id do SofaScore (sofa_XXXX)
                # 3. Depois, o que tem status "FT" / "Finished"
                # 4. Por último, o de ID menor (mais antigo)
                def sort_key(m):
                    # Time pertence à liga correta?
                    home_correct_league = 1 if m.home_team.league_id == league.id else 0
                    away_correct_league = 1 if m.away_team.league_id == league.id else 0
                    both_correct = home_correct_league + away_correct_league  # 0, 1, or 2
                    
                    has_sofa_id = 1 if (m.api_id and m.api_id.startswith('sofa_')) else 0
                    is_finished = 1 if m.status in FINISHED_STATUSES else 0
                    has_score = 1 if (m.home_score is not None and m.away_score is not None) else 0
                    return (-both_correct, -has_sofa_id, -is_finished, -has_score, m.id)

                match_list.sort(key=sort_key)
                keeper = match_list[0]
                to_delete = match_list[1:]

                self.stdout.write(
                    f"    ✅ Mantendo ID: {keeper.id} | api_id: {keeper.api_id} | "
                    f"status: {keeper.status} | placar: {keeper.home_score}-{keeper.away_score} | "
                    f"home_team: {keeper.home_team.name} (liga: {keeper.home_team.league.name})"
                )

                for d in to_delete:
                    self.stdout.write(
                        f"    🗑️  Deletando ID: {d.id} | api_id: {d.api_id} | "
                        f"status: {d.status} | placar: {d.home_score}-{d.away_score} | "
                        f"home_team: {d.home_team.name} (liga: {d.home_team.league.name})"
                    )
                    if not dry_run:
                        # Mescla dados do duplicado para o keeper antes de deletar
                        merged, goals_moved = self._merge_match_data(keeper, d)
                        if merged:
                            self.stdout.write(f"      📦 Dados mesclados para o keeper.")
                        if goals_moved > 0:
                            self.stdout.write(f"      ⚽ {goals_moved} gol(s) movido(s) para o keeper.")
                        d.delete()
                        league_deleted += 1

            if league_deleted > 0:
                self.stdout.write(self.style.SUCCESS(f"  → {league_deleted} duplicata(s) removida(s) de {league.name}."))
            else:
                self.stdout.write(f"  → Nenhuma duplicata encontrada em {league.name}.")

            total_deleted += league_deleted

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Concluído! Total de duplicatas removidas: {total_deleted}")
        )
