"""
full_sync_league.py
====================
Comando ALL-IN-ONE para sincronizar uma liga do localhost para o servidor.

Uso:
  python manage.py full_sync_league --liga 7
  python manage.py full_sync_league --liga 7 --push
  python manage.py full_sync_league --liga 7 --push --auto-commit

Flags:
  --liga ID       ID da liga no banco (obrigatório)
  --push          Faz git add, commit, push automaticamente
  --auto-commit   Gera mensagem de commit automaticamente
  --dry-run       Mostra o que faria sem executar

Ligas disponíveis:
  2   - America do Sul - Copa Libertadores
  3   - America do Sul - Copa Sul-Americana
  7   - Alemanha - Bundesliga
  8   - Argentina - Liga Profesional
  13  - Brasil - Brasileirao
  17  - Espanha - La Liga
  21  - Franca - Ligue 1
  44  - Inglaterra - Championship
  45  - Inglaterra - Premier League
  49  - Italia - Serie A
  53  - America do Sul - Copa Sul-Americana
  (consulte o banco para outros IDs)
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from matches.models import League, Match


class Command(BaseCommand):
    help = "ALL-IN-ONE: exporta deep scrape, salva JSON, commita e push"

    def add_arguments(self, parser):
        parser.add_argument('--liga', type=int, required=True, help='ID da liga')
        parser.add_argument('--push', action='store_true', help='Faz git push automaticamente')
        parser.add_argument('--auto-commit', action='store_true', help='Gera mensagem de commit')
        parser.add_argument('--dry-run', action='store_true', help='Só mostra o que faria')

    def handle(self, *args, **options):
        league_id = options['liga']
        do_push = options.get('push', False)
        auto_commit = options.get('auto_commit', False)
        dry_run = options.get('dry_run', False)

        # 1. Descobre o nome da liga
        league = League.objects.filter(id=league_id).first()
        if not league:
            self.stdout.write(self.style.ERROR(f'Liga ID {league_id} não encontrada!'))
            return

        liga_nome = f"{league.country} - {league.name}"
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS(f"  🚀 FULL SYNC: {liga_nome} (ID: {league_id})"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}\n"))

        # 2. Exporta deep scrape
        output_file = 'deep_scrape_exports/dados_deep_scrape.json'
        self.stdout.write(f"📤 Exportando deep scrape...")

        if not dry_run:
            try:
                call_command(
                    'export_deep_scrape',
                    liga=league_id,
                    output=f"/app/{output_file}"
                )
                self.stdout.write(self.style.SUCCESS(f"  ✅ Exportado para {output_file}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Erro no export: {e}"))
                return
        else:
            self.stdout.write("  🔍 DRY-RUN: pularia export")

        # 3. Copia do Docker pro Windows
        self.stdout.write(f"📋 Copiando do Docker pro Windows...")
        if not dry_run:
            result = os.system(
                f'docker compose cp web:/app/{output_file} {output_file}'
            )
            if result == 0:
                self.stdout.write(self.style.SUCCESS(f"  ✅ Copiado para {output_file}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ Erro ao copiar"))
                return
        else:
            self.stdout.write("  🔍 DRY-RUN: pularia copy")

        # 4. Conta partidas e gols
        if not dry_run:
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                total = len(data)
                total_goals = sum(len(d['goals']) for d in data)
                self.stdout.write(f"  📊 {total} partidas, {total_goals} gols")
            except:
                pass

        # 5. Git add + commit + push
        if do_push:
            self.stdout.write(f"\n📦 Preparando git...")

            # Mensagem automática
            if auto_commit:
                now = datetime.now().strftime("%d/%m/%Y %H:%M")
                msg = f"Deep Scrape: {liga_nome} ({total} partidas, {total_goals} gols) - {now}"
            else:
                msg = f"Deep Scrape: {liga_nome}"

            if not dry_run:
                # git add
                r = os.system(f'git add {output_file}')
                if r != 0:
                    self.stdout.write(self.style.ERROR("  ❌ Erro no git add"))
                    return

                # git commit
                r = os.system(f'git commit -m "{msg}"')
                if r != 0:
                    self.stdout.write(self.style.WARNING("  ⚠️ Nada pra commitar (ou erro)"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Commit: {msg}"))

                # git push
                self.stdout.write(f"  📤 Fazendo push...")
                r = os.system('git push origin main')
                if r == 0:
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Push realizado!"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ Erro no push"))
                    return
            else:
                self.stdout.write(f"  🔍 DRY-RUN: git add + commit + push")
        else:
            self.stdout.write(f"\n  💡 Use --push para commitar e enviar ao GitHub")

        # 6. Instruções finais
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"  ✅ FULL SYNC CONCLUÍDO!"))
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"\n  📋 Agora no SERVIDOR (VPS), rode:")
        self.stdout.write(f"\n    cd /www/wwwroot/statsfut.com")
        self.stdout.write(f"    git pull origin main")
        self.stdout.write(f"    python manage.py import_deep_scrape deep_scrape_exports/dados_deep_scrape.json")
        self.stdout.write(f"    python manage.py shell -c \"from django.core.cache import cache; cache.clear()\"")
        self.stdout.write(f"    sudo systemctl restart statsfut")
        self.stdout.write(f"\n{'='*60}\n")
