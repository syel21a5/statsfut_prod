import os
import json
import subprocess
from textwrap import dedent
import re

def remover_acentos(texto):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def main():
    print("=" * 60)
    print(" 🚀 GERADOR AUTOMÁTICO DE LIGAS (STATS FUT) 🚀 ")
    print("=" * 60)
    print("Este script vai criar os arquivos históricos automaticamente sem gastar tokens!")
    print("")

    # Configurar path para importar o matches.utils
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from matches.utils import get_flag_code, COUNTRY_REVERSE_TRANSLATIONS

    # Coleta de dados via Link
    url = input("Cole o link da liga do SofaScore (ex: https://www.sofascore.com/...): ").strip()
    
    match = re.search(r'tournament/([^/]+)/([^/]+)/(\d+)', url)
    if not match:
        print("\n❌ Erro: URL inválida. Certifique-se de colar a URL completa da liga do SofaScore.")
        return
        
    slug_pais = match.group(1).lower()
    slug_liga = match.group(2)
    tournament_id = match.group(3)
    
    # Auto-completar dados
    nome_liga = slug_liga.replace('-', ' ').title()
    pais = COUNTRY_REVERSE_TRANSLATIONS.get(slug_pais, slug_pais.title())
    flag_code = get_flag_code(slug_pais)
    
    if flag_code == 'xx':
        flag_code = input(f"⚠️ Não achei a bandeira para {slug_pais}. Digite o código ISO de 2 letras (ex: br, ec): ").strip().lower()
        
    print("\n✅ Dados identificados automaticamente a partir do link:")
    print(f"   Nome da Liga: {nome_liga}")
    print(f"   País: {pais}")
    print(f"   Slug: {slug_pais}")
    print(f"   ID SofaScore: {tournament_id}")
    print(f"   Bandeira: {flag_code}")
    
    confirma = input("\nOs dados acima estão corretos? (s/n): ").strip().lower()
    if confirma != 's':
        print("Operação cancelada.")
        return

    nome_liga_limpo = remover_acentos(nome_liga)
    pais_limpo = remover_acentos(pais)

    # Buscar seasons automaticamente
    print(f"\n⏳ Buscando temporadas do torneio {tournament_id} na API do SofaScore...")
    try:
        resultado = subprocess.run(
            ["python", "proxy_sofascore_fetcher.py", "--tournament", tournament_id, "--list-seasons"],
            capture_output=True,
            text=True,
            check=True
        )
        seasons_data = json.loads(resultado.stdout)
    except Exception as e:
        print(f"❌ Erro ao buscar temporadas: {e}")
        print("Saída do comando:", resultado.stderr if 'resultado' in locals() else "N/A")
        return

    # Extrair e filtrar temporadas >= 2020
    # Suporta formatos: "2025" (ligas sul-americanas) e "25/26" (ligas europeias)
    seasons_dict = {}
    for season in seasons_data:
        try:
            raw_year = season.get('year', '0')
            if isinstance(raw_year, str) and '/' in raw_year:
                # Formato europeu: "25/26" -> 2025
                first_part = int(raw_year.split('/')[0])
                year = first_part + 2000 if first_part < 100 else first_part
            elif isinstance(raw_year, str):
                # Formato normal: "2025"
                year = int(raw_year[:4])
            else:
                year = int(raw_year)
            if year >= 2020:
                seasons_dict[year] = season['id']
        except Exception:
            pass
            
    if not seasons_dict:
        print("❌ Não foi encontrada nenhuma temporada de 2020 em diante.")
        return
        
    latest_year = max(seasons_dict.keys())
    latest_season_id = seasons_dict[latest_year]
    
    print("\n✅ Temporadas encontradas:")
    for y, sid in sorted(seasons_dict.items()):
        print(f"   {y}: {sid}")

    # =========================================================================
    # 1. GERAR FETCH SCRIPT
    # =========================================================================
    seasons_formatted = ",\n".join([f"            {y}: {sid}" for y, sid in sorted(seasons_dict.items())])
    fetch_content = dedent(f'''\
        import subprocess
        import os
        import shutil

        seasons = {{
{seasons_formatted}
        }}

        output_dir = "historical_data/{pais_limpo}/{nome_liga_limpo.replace(' ', '')}"
        os.makedirs(output_dir, exist_ok=True)

        print("Iniciando a busca histórica de {pais_limpo}...")

        for year, season_id in seasons.items():
            print(f"\\n--- Buscando Temporada {{year}} (SofaScore ID: {{season_id}}) ---")
            
            # Executa o fetcher
            cmd = ["python", "proxy_sofascore_fetcher.py", "--tournament", "{tournament_id}", "--season", str(season_id)]
            subprocess.run(cmd)
            
            # Move payload.json gerado para a pasta histórica
            src = "payload.json"
            dst = os.path.join(output_dir, f"{{year}}.json")
            
            if os.path.exists(src):
                shutil.move(src, dst)
                print(f"✅ Temporada {{year}} salva com sucesso em {{dst}}")
            else:
                print(f"❌ Erro ao gerar payload para a temporada {{year}}")

        print("\\n🎉 Todas as temporadas de {pais_limpo} foram baixadas com sucesso!")
    ''').strip() + "\n"

    fetch_path = f"historical_data/fetch_{slug_pais}.py"
    with open(fetch_path, "w", encoding="utf-8") as f:
        f.write(fetch_content)
    print(f"✅ Criado: {fetch_path}")

    # =========================================================================
    # 2. GERAR HIST COMMAND
    # =========================================================================
    hist_content = dedent(f'''\
        import os
        import json
        from django.core.management.base import BaseCommand  # type: ignore
        from django.core.management import call_command  # type: ignore
        from matches.models import League

        class Command(BaseCommand):
            help = "Importa automaticamente todos os payloads JSON históricos de {pais} ({nome_liga})."

            def handle(self, *args, **options):
                base_dir = "historical_data/{pais_limpo}/{nome_liga_limpo.replace(' ', '')}"
                
                if not os.path.exists(base_dir):
                    self.stdout.write(self.style.ERROR(f"Diretório {{base_dir}} não encontrado!"))  # type: ignore
                    return

                league, created = League.objects.get_or_create(name='{nome_liga_limpo}', country='{pais_limpo}')  # type: ignore
                if created:
                    self.stdout.write(self.style.SUCCESS("Liga '{nome_liga_limpo}' ({pais_limpo}) criada no banco."))  # type: ignore

                self.stdout.write(self.style.SUCCESS(f"Iniciando importação histórica para {{league.name}} (ID: {{league.id}})"))  # type: ignore

                for year in range(2020, {latest_year + 1}):
                    filename = f"{{base_dir}}/{{year}}.json"
                    if os.path.exists(filename):
                        self.stdout.write(self.style.WARNING(f"\\n>>> Importando ano {{year}}..."))  # type: ignore
                        try:
                            call_command('import_sofascore_payload', file=filename, league_id=league.id, season_year=year)
                            self.stdout.write(self.style.SUCCESS(f"-> Sucesso ao importar {{year}}.json"))  # type: ignore
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"-> Erro ao importar {{year}}.json: {{e}}"))  # type: ignore
                    else:
                        self.stdout.write(self.style.NOTICE(f"Arquivo não encontrado: {{filename}}"))  # type: ignore

                self.stdout.write(self.style.WARNING("\\nRecalculando tabelas..."))  # type: ignore
                for year in range(2020, {latest_year + 1}):
                     call_command('recalculate_standings', league_name='{nome_liga_limpo}', country='{pais_limpo}', season_year=year)

                self.stdout.write(self.style.SUCCESS(f"\\n✅ Importação histórica de {pais_limpo} concluída!"))  # type: ignore
    ''')

    hist_path = f"matches/management/commands/hist_{slug_pais}.py"
    with open(hist_path, "w", encoding="utf-8") as f:
        f.write(hist_content)
    print(f"✅ Criado: {hist_path}")

    # =========================================================================
    # 3. GERAR GITHUB ACTION
    # =========================================================================
    github_content = dedent(f'''\
        # yaml-language-server: $schema=https://json.schemastore.org/github-workflow.json
        name: Update {pais_limpo} Data via SofaScore

        on:
          schedule:
            # Executa todos os dias às 13:00 UTC
            - cron: '0 13 * * *'
          workflow_dispatch:
            inputs:
              full_scan:
                description: 'Fazer carga total de todas as rodadas?'
                required: true
                type: boolean
                default: false

        jobs:
          update-{slug_pais}:
            runs-on: ubuntu-latest
            timeout-minutes: 20

            steps:
              - name: Checkout código
                uses: actions/checkout@v4

              - name: Instalar uv
                uses: astral-sh/setup-uv@v5
                with:
                  enable-cache: true

              - name: Configurar Python
                uses: actions/setup-python@v5
                with:
                  python-version: '3.12'

              - name: Instalar dependências
                run: |
                  uv pip install --system curl_cffi requests

              - name: WARP
                uses: fscarmen/warp-on-actions@v1.2
                with:
                  stack: dual

              - name: Rodar fetcher ({pais_limpo})
                run: |
                  if [ "${{{{ github.event.inputs.full_scan }}}}" == "true" ]; then
                    python proxy_sofascore_fetcher.py --tournament {tournament_id} --season {latest_season_id}
                  else
                    python proxy_sofascore_fetcher.py --tournament {tournament_id} --season {latest_season_id} --last-rounds 3
                  fi

              - name: Enviar payload e processar na VPS
                env:
                  PROD_SERVER_HOST: ${{{{ secrets.PROD_SERVER_HOST }}}}
                  PROD_SERVER_USER: root
                  PROD_SERVER_PATH: ${{{{ secrets.PROD_SERVER_PATH }}}}
                  SSH_PRIVATE_KEY: ${{{{ secrets.SSH_PRIVATE_KEY }}}}
                run: |
                  mkdir -p ~/.ssh
                  echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_rsa
                  chmod 600 ~/.ssh/id_rsa
                  
                  scp -o StrictHostKeyChecking=no payload.json $PROD_SERVER_USER@$PROD_SERVER_HOST:$PROD_SERVER_PATH/payload_{slug_pais}.json
                  
                  ssh -o StrictHostKeyChecking=no $PROD_SERVER_USER@$PROD_SERVER_HOST "
                    cd $PROD_SERVER_PATH
                    git pull origin main
                    ./venv/bin/python manage.py import_sofascore_payload --file payload_{slug_pais}.json --league_name \\"{nome_liga_limpo}\\" --country \\"{pais_limpo}\\" --season_year {latest_year}
                    ./venv/bin/python manage.py merge_duplicate_teams
                    ./venv/bin/python manage.py recalculate_standings --league_name \\"{nome_liga_limpo}\\" --country \\"{pais_limpo}\\" --season_year {latest_year}

                    rm payload_{slug_pais}.json
                  "
    ''')

    action_path = f".github/workflows/update_{slug_pais}.yml"
    with open(action_path, "w", encoding="utf-8") as f:
        f.write(github_content)
    print(f"✅ Criado: {action_path}")

    # =========================================================================
    # 4. AUTO-INSERIR EM import_all_leagues.py
    # =========================================================================
    all_leagues_path = "matches/management/commands/import_all_leagues.py"
    new_mapping_line = f"            'payload_{slug_pais}.json': {{'name': '{nome_liga_limpo}', 'country': '{pais_limpo}'}},"
    
    with open(all_leagues_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if f"payload_{slug_pais}.json" not in content:
        # Insere antes do fechamento do dicionário mapping (a linha com apenas "}")
        content = content.replace(
            "        }\n\n        self.stdout.write",
            f"{new_mapping_line}\n        }}\n\n        self.stdout.write"
        )
        with open(all_leagues_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Inserido em: {all_leagues_path}")
    else:
        print(f"⚠️ Já existe em: {all_leagues_path} (pulando)")

    # =========================================================================
    # 5. AUTO-INSERIR EM utils.py (COUNTRY_TRANSLATIONS + get_flag_code)
    # =========================================================================
    utils_path = "matches/utils.py"
    
    with open(utils_path, "r", encoding="utf-8") as f:
        utils_content = f.read()
    
    utils_modified = False
    
    # 5a. COUNTRY_TRANSLATIONS
    country_english = COUNTRY_REVERSE_TRANSLATIONS.get(slug_pais, slug_pais.title())
    # Inverter: precisamos PT -> EN
    # Verificar se o COUNTRY_TRANSLATIONS tem essa entrada via dict reverso
    from matches.utils import COUNTRY_TRANSLATIONS
    if pais_limpo not in COUNTRY_TRANSLATIONS:
        new_translation = f'    "{pais_limpo}": "{country_english}",\n'
        # Insere antes do fechamento do COUNTRY_TRANSLATIONS
        marker = "}\n\nCOUNTRY_REVERSE_TRANSLATIONS"
        if marker in utils_content:
            utils_content = utils_content.replace(marker, f'{new_translation}}}\n\nCOUNTRY_REVERSE_TRANSLATIONS')
            utils_modified = True
            print(f"✅ Inserido COUNTRY_TRANSLATIONS: '{pais_limpo}': '{country_english}'")
    else:
        print(f"⚠️ COUNTRY_TRANSLATIONS já tem '{pais_limpo}' (pulando)")

    # 5b. get_flag_code mapping
    if f"'{pais_limpo.lower()}'" not in utils_content and f"'{slug_pais}'" not in utils_content:
        new_flag_line = f"        '{pais_limpo.lower()}': '{flag_code}',\n"
        new_flag_line_en = f"        '{slug_pais}': '{flag_code}',\n"
        marker2 = "    }\n    \n    return mapping.get"
        if marker2 in utils_content:
            utils_content = utils_content.replace(marker2, f'{new_flag_line}{new_flag_line_en}    }}\n    \n    return mapping.get')
            utils_modified = True
            print(f"✅ Inserido get_flag_code: '{pais_limpo.lower()}': '{flag_code}'")
        else:
            # Tenta marcador alternativo
            marker2b = "    }\n\n    return mapping.get"
            if marker2b in utils_content:
                utils_content = utils_content.replace(marker2b, f'{new_flag_line}{new_flag_line_en}    }}\n\n    return mapping.get')
                utils_modified = True
                print(f"✅ Inserido get_flag_code: '{pais_limpo.lower()}': '{flag_code}'")
    else:
        print(f"⚠️ get_flag_code já tem '{pais_limpo.lower()}' (pulando)")
    
    if utils_modified:
        with open(utils_path, "w", encoding="utf-8") as f:
            f.write(utils_content)

    # =========================================================================
    # 6. AUTO-INSERIR BANDEIRA EM base.html
    # =========================================================================
    base_html_path = "core/templates/base.html"
    
    with open(base_html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    if f"'{slug_pais}'" not in html_content:
        # Encontrar a linha de título correta para o país em inglês
        country_title = country_english if country_english != slug_pais.title() else pais_limpo
        new_flag_btn = f'            <a href="{{% url \'matches:country_stats\' \'{slug_pais}\' %}}" class="flag-btn" data-bs-toggle="tooltip" title="{country_title}"><span class="fi fi-{flag_code}"></span></a>\r\n'
        
        # Inserir na ordem alfabética por slug dentro da seção de bandeiras
        # Encontrar todas as linhas de bandeira e inserir na posição correta
        lines = html_content.split('\n')
        insert_index = None
        flag_section_end = None
        
        for i, line in enumerate(lines):
            if "country_stats" in line and "flag-btn" in line:
                # Extrair o slug desta linha
                import re as re2
                slug_match = re2.search(r"country_stats' '([^']+)'", line)
                if slug_match:
                    existing_slug = slug_match.group(1)
                    if existing_slug > slug_pais and insert_index is None:
                        insert_index = i
                flag_section_end = i + 1
        
        if insert_index is None and flag_section_end is not None:
            insert_index = flag_section_end  # Adicionar no final se é o último alfabeticamente
        
        if insert_index is not None:
            lines.insert(insert_index, new_flag_btn.rstrip('\r\n'))
            html_content = '\n'.join(lines)
            with open(base_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"✅ Inserido bandeira em: {base_html_path}")
        else:
            print(f"⚠️ Não consegui encontrar a seção de bandeiras em base.html")
    else:
        print(f"⚠️ Bandeira já existe em: {base_html_path} (pulando)")

    # =========================================================================
    # RESUMO FINAL
    # =========================================================================
    print(f"\n{'='*60}")
    print(f" 🎉 TUDO PRONTO! LIGA CRIADA 100% AUTOMATICAMENTE! 🎉")
    print(f"{'='*60}")
    print(f"\n📁 Arquivos criados:")
    print(f"   ✅ {fetch_path}")
    print(f"   ✅ {hist_path}")
    print(f"   ✅ {action_path}")
    print(f"\n📝 Arquivos modificados:")
    print(f"   ✅ {all_leagues_path}")
    print(f"   ✅ {utils_path}")
    print(f"   ✅ {base_html_path}")
    print(f"\n{'='*60}")
    print(f"PRÓXIMOS PASSOS (OPCIONAL):")
    print(f"1. Para baixar dados históricos: python historical_data/fetch_{slug_pais}.py")
    print(f"2. Para importar no banco:       python manage.py hist_{slug_pais}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

