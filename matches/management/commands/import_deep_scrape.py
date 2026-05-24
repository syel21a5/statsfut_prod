"""
Importa dados do Deep Scrape (estatísticas avançadas + gols) a partir de JSON.

Uso:
  python manage.py import_deep_scrape dados_deep_scrape.json
  python manage.py import_deep_scrape dados_deep_scrape.json --dry-run
"""
import json
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from matches.models import Match, Goal, Team


class Command(BaseCommand):
    help = "Importa dados do Deep Scrape (escanteios, cartões, chutes, gols) de um JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Arquivo JSON com os dados exportados'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostra o que seria importado, sem alterar o banco'
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        dry_run = options.get('dry_run', False)

        if not os.path.exists(json_file):
            self.stdout.write(self.style.ERROR(f"Arquivo {json_file} não encontrado!"))
            return

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.stdout.write(f"📥 Importando {len(data)} partidas...")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 Modo DRY-RUN: nenhuma alteração será feita.\n"))

        stats_updated = 0
        goals_updated = 0
        errors = 0
        skipped = 0

        for item in data:
            api_id = item['api_id']
            if not api_id:
                skipped += 1
                continue

            # Encontra a partida pelo api_id
            match = Match.objects.filter(api_id=api_id).first()
            
            # FALLBACK: Se não achou pelo api_id, tenta por nome dos times + data + liga
            if not match:
                home_team_name = item.get('home_team', '')
                away_team_name = item.get('away_team', '')
                match_date = item.get('date')
                league_name = item.get('league_name')
                league_country = item.get('league_country')
                
                # Tenta pela data e nomes dos times
                from django.utils.dateparse import parse_datetime
                from datetime import datetime
                
                if match_date and home_team_name and away_team_name:
                    # Normaliza a data (pega só a parte da data, sem hora)
                    try:
                        dt = parse_datetime(match_date.replace('Z', '+00:00')) if 'Z' in str(match_date) or '+' in str(match_date) else datetime.fromisoformat(str(match_date))
                        date_only = dt.date()
                    except:
                        dt = None
                        date_only = None
                    
                    if date_only:
                        # Busca por data + nomes aproximados dos times
                        from django.db.models import Q
                        
                        # Filtra por dia +/- 1 dia
                        from datetime import timedelta
                        day_start = datetime.combine(date_only, datetime.min.time())
                        day_end = datetime.combine(date_only, datetime.max.time())
                        
                        candidates = Match.objects.filter(
                            date__range=(day_start, day_end),
                        )
                        
                        # Filtra por nomes dos times (case insensitive)
                        for candidate in candidates:
                            h_name = candidate.home_team.name.lower() if candidate.home_team else ''
                            a_name = candidate.away_team.name.lower() if candidate.away_team else ''
                            h_search = home_team_name.lower()
                            a_search = away_team_name.lower()
                            
                            # Verifica se os nomes combinam (pelo menos parte do nome)
                            h_match = h_search in h_name or h_name in h_search or h_search.split()[0] in h_name.split() if h_search.split() else False
                            a_match = a_search in a_name or a_name in a_search or a_search.split()[0] in a_name.split() if a_search.split() else False
                            
                            if h_match and a_match:
                                match = candidate
                                self.stdout.write(self.style.SUCCESS(
                                    f"  ✅ Partida encontrada por fallback: {api_id} -> "
                                    f"{candidate.home_team.name} x {candidate.away_team.name} (api_id: {candidate.api_id})"
                                ))
                                break
            
            if not match:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠️ Partida não encontrada: {api_id} "
                    f"({item.get('home_team')} x {item.get('away_team')})"
                ))
                errors += 1
                continue

            # Atualiza as estatísticas
            stats = item['stats']
            has_stats = any(v is not None for v in stats.values())

            if has_stats:
                if not dry_run:
                    for field, value in stats.items():
                        if value is not None:
                            setattr(match, field, value)
                    match.save()
                stats_updated += 1

            # Importa os gols
            if item['goals']:
                if not dry_run:
                    with transaction.atomic():
                        # Remove gols antigos
                        Goal.objects.filter(match=match).delete()
                        
                        for gol_data in item['goals']:
                            team_name = gol_data.get('team_name', '')
                            team = None
                            
                            # Estratégia 1 (MELHOR): Usar is_home se disponível
                            is_home = gol_data.get('is_home')
                            if is_home is not None:
                                team = match.home_team if is_home else match.away_team
                            
                            # Estratégia 2: Nome exato
                            if not team and team_name:
                                if match.home_team and match.home_team.name == team_name:
                                    team = match.home_team
                                elif match.away_team and match.away_team.name == team_name:
                                    team = match.away_team
                            
                            # Estratégia 3: Parte do nome (ex: "Estudiantes L.P." ~ "Estudiantes de La Plata")
                            if not team and team_name:
                                home_name = match.home_team.name.lower() if match.home_team else ''
                                away_name = match.away_team.name.lower() if match.away_team else ''
                                team_name_lower = team_name.lower()
                                
                                if home_name and (team_name_lower in home_name or home_name in team_name_lower):
                                    team = match.home_team
                                elif away_name and (team_name_lower in away_name or away_name in team_name_lower):
                                    team = match.away_team
                                
                                # Estratégia 4: Primeira palavra do nome
                                if not team:
                                    first_word = team_name.split()[0].lower() if team_name.split() else ''
                                    if home_name and first_word and first_word in home_name:
                                        team = match.home_team
                                    elif away_name and first_word and first_word in away_name:
                                        team = match.away_team
                            
                            if not team:
                                self.stdout.write(self.style.WARNING(
                                    f"    ⚠️ Time não encontrado para gol: {gol_data.get('player_name')} "
                                    f"em {match.home_team} x {match.away_team} (time: {team_name})"
                                ))
                                continue
                            
                            Goal.objects.create(
                                match=match,
                                team=team,
                                player_name=gol_data['player_name'],
                                minute=gol_data['minute'],
                                is_own_goal=gol_data.get('is_own_goal', False),
                                is_penalty=gol_data.get('is_penalty', False),
                            )
                goals_updated += len(item['goals'])

        # Resumo
        self.stdout.write(f"\n{'=' * 50}")
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY-RUN - Nada foi alterado!"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Importação concluída!"))
        self.stdout.write(f"   📊 {stats_updated} partidas com stats atualizadas")
        self.stdout.write(f"   ⚽ {goals_updated} gols importados")
        self.stdout.write(f"   ❌ {errors} erros (partidas não encontradas)")
        self.stdout.write(f"   ⏭️  {skipped} puladas (sem api_id)")
        
        if errors > 0:
            self.stdout.write(self.style.WARNING(
                "\n💡 Dica: As partidas não encontradas podem ter sido importadas "
                "com outro api_id ou podem não existir no servidor ainda. "
                "Execute 'sync_all_fixtures' primeiro para garantir que as partidas existem."
            ))

    def _import_deep_scrape(self, json_file):
        """Função pública para ser chamada de outros scripts."""
        self.handle(json_file=json_file)
