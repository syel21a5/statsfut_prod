import os
import random
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.utils.text import slugify

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from matches.models import Match, LeagueStanding


class Command(BaseCommand):
    help = "Busca jogos do Brasileirão Série A e B de amanhã, gera artigos de análise com IA e publica no statsfutbrasil com foco em SEO avançado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Data alvo no formato AAAA-MM-DD (Padrão: Amanhã no fuso de Brasília)."
        )
        parser.add_argument(
            "--test-run",
            action="store_true",
            help="Executa a geração mas apenas exibe o HTML no terminal sem publicar."
        )

    def handle(self, *args, **options):
        # 1. Configurar data alvo (Amanhã no fuso de Brasília)
        br_tz = ZoneInfo("America/Sao_Paulo")
        now_br = timezone.now().astimezone(br_tz)
        
        if options["date"]:
            try:
                target_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                self.stderr.write("Formato de data inválido. Use AAAA-MM-DD.")
                return
        else:
            target_date = (now_br + timedelta(days=1)).date()

        self.stdout.write(f"Buscando jogos do Brasileirão para a data: {target_date}...")

        # 2. Buscar partidas do Brasileirão Série A e Série B para o dia seguinte
        matches = Match.objects.filter(
            date__date=target_date,
            league__name__icontains="Série"
        ).filter(
            league__country="Brasil"
        ).select_related("league", "home_team", "away_team").order_by("date")

        if not matches.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Nenhuma partida do Brasileirão Série A ou B encontrada no banco para {target_date}."
                )
            )
            return

        # Agrupar partidas por Liga
        leagues_dict = {}
        for m in matches:
            l_name = m.league.name
            if l_name not in leagues_dict:
                leagues_dict[l_name] = []
            leagues_dict[l_name].append(m)

        # 3. Autenticação na API do Blogger
        blogger_service = None
        if not options["test_run"]:
            self.stdout.write("Conectando à API do Blogger...")
            try:
                blogger_service = self.get_blogger_service()
            except Exception as e:
                self.stderr.write(f"Erro ao autenticar com o Blogger: {e}")
                return

        # 4. Processar e publicar posts por liga
        for league_name, league_matches in leagues_dict.items():
            self.stdout.write(f"\nProcessando {len(league_matches)} jogos para {league_name}...")
            
            # Ordenamos os confrontos pela soma de pontos de ambos os times na tabela atual (Mais importantes primeiro)
            def get_match_importance(match):
                home_pts = 0
                away_pts = 0
                home_standing = LeagueStanding.objects.filter(league=match.league, team=match.home_team).first()
                away_standing = LeagueStanding.objects.filter(league=match.league, team=match.away_team).first()
                if home_standing:
                    home_pts = home_standing.points
                if away_standing:
                    away_pts = away_standing.points
                return home_pts + away_pts

            sorted_matches = sorted(league_matches, key=get_match_importance, reverse=True)
            
            # Gerar a tabela do cronograma dos jogos no topo
            table_html = self.generate_matches_table(league_matches)
            
            # Selecionar até 3 jogos principais (destaques) para análise detalhada com IA
            featured_matches = sorted_matches[:3]
            
            # Título focado em SEO Avançado com confrontos reais
            if len(featured_matches) >= 2:
                t_home1, t_away1 = featured_matches[0].home_team.name, featured_matches[0].away_team.name
                t_home2, t_away2 = featured_matches[1].home_team.name, featured_matches[1].away_team.name
                title = f"{league_name} amanhã: {t_home1} x {t_away1}, {t_home2} x {t_away2} | Análise e Estatísticas da Rodada ({target_date.strftime('%d/%m')})"
            elif len(featured_matches) == 1:
                t_home1, t_away1 = featured_matches[0].home_team.name, featured_matches[0].away_team.name
                title = f"{league_name} amanhã: {t_home1} x {t_away1} | Análise e Estatísticas da Rodada ({target_date.strftime('%d/%m')})"
            else:
                title = f"{league_name} amanhã: Estatísticas e Análise da Rodada ({target_date.strftime('%d/%m/%Y')})"
            
            html_analysis = self.generate_analysis_via_gemini(league_name, featured_matches)
            
            if not html_analysis:
                self.stderr.write(f"Falha ao gerar conteúdo para {league_name}. Pulando...")
                continue

            # Montar template final de post
            html_content = self.assemble_final_html(league_name, table_html, html_analysis, target_date)

            # 5. Enviar ou Exibir em Modo Teste
            if options["test_run"]:
                self.stdout.write(self.style.SUCCESS(f"\n=== MODO TESTE ATIVO ({league_name}) ==="))
                self.stdout.write(f"Título: {title}")
                self.stdout.write("Conteúdo HTML:")
                self.stdout.write("-" * 50)
                self.stdout.write(html_content)
                self.stdout.write("-" * 50)
            else:
                self.stdout.write(f"Publicando post no blog 'StatsFut Brasil' ({league_name})...")
                blog_id = "6808698508164581615"
                
                body = {
                    "kind": "blogger#post",
                    "blog": {"id": blog_id},
                    "title": title,
                    "content": html_content,
                    "labels": [league_name, "Análise de Futebol", "Estatísticas de Futebol", "Futebol Brasileiro"]
                }

                try:
                    post = blogger_service.posts().insert(blogId=blog_id, body=body).execute()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Post publicado com sucesso no Blogger! URL: {post.get('url')}"
                        )
                    )
                except Exception as e:
                    self.stderr.write(f"Erro ao inserir post no Blogger: {e}")

    def get_blogger_service(self):
        """Gerencia o fluxo de token e retorna o cliente de serviço da API do Blogger."""
        scopes = ["https://www.googleapis.com/auth/blogger"]
        token_path = os.path.join(settings.BASE_DIR, "token.json")
        secrets_path = os.path.join(settings.BASE_DIR, "client_secrets.json")

        if not os.path.exists(secrets_path):
            raise FileNotFoundError(
                f"Arquivo client_secrets.json não encontrado em: {secrets_path}. Por favor, adicione-o."
            )

        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, scopes)
                creds = flow.run_local_server(port=0)
            
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())

        return build("blogger", "v3", credentials=creds)

    def generate_matches_table(self, matches):
        """Gera uma tabela HTML de cronograma super limpa e profissional com escudos dos times."""
        rows = ""
        br_tz = ZoneInfo("America/Sao_Paulo")
        domain = "https://statsfut.com"
        
        for m in matches:
            horario_br = m.date.astimezone(br_tz).strftime("%H:%M")
            slug = slugify(f"{m.home_team.name}-vs-{m.away_team.name}")
            match_url = f"{domain}/match/{m.id}/{slug}/"
            
            logo_home = f"{domain}{m.home_team.logo_url}" if m.home_team.logo_url else ""
            logo_away = f"{domain}{m.away_team.logo_url}" if m.away_team.logo_url else ""
            
            img_home = f'<img src="{logo_home}" width="20" height="20" style="vertical-align: middle; margin-right: 6px; object-fit: contain;" alt="{m.home_team.name}" />' if logo_home else ""
            img_away = f'<img src="{logo_away}" width="20" height="20" style="vertical-align: middle; margin-left: 6px; margin-right: 6px; object-fit: contain;" alt="{m.away_team.name}" />' if logo_away else ""
            
            rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; hover: background-color: #f8fafc;">
                <td style="padding: 12px; font-weight: bold; color: #1e293b; display: flex; align-items: center; gap: 4px;">
                    {img_home}
                    <span>{m.home_team.name}</span>
                    <span style="color: #94a3b8; font-weight: normal; margin: 0 4px;">vs</span>
                    <span>{m.away_team.name}</span>
                    {img_away}
                </td>
                <td style="padding: 12px; color: #475569; text-align: center; font-weight: 500;">{horario_br}</td>
                <td style="padding: 12px; text-align: right;">
                    <a href="{match_url}" style="background-color: #2e7d32; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 0.85em; display: inline-block;">Ver Estatísticas 📊</a>
                </td>
            </tr>
            """

        table = f"""
        <div style="margin: 25px 0; overflow-x: auto; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-radius: 8px; border: 1px solid #e2e8f0;">
            <table style="width: 100%; border-collapse: collapse; text-align: left; font-family: sans-serif; font-size: 0.95em; min-width: 500px;">
                <thead>
                    <tr style="background-color: #f8fafc; border-bottom: 2px solid #e2e8f0;">
                        <th style="padding: 12px; color: #334155; font-weight: bold;">Partida</th>
                        <th style="padding: 12px; color: #334155; font-weight: bold; text-align: center;">Horário</th>
                        <th style="padding: 12px; color: #334155; font-weight: bold; text-align: right;">Dados do Jogo</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
        return table

    def generate_analysis_via_gemini(self, league_name, matches):
        """Usa a API do Gemini para gerar análises táticas no novo padrão premium em caixas organizadas."""
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            self.stdout.write(self.style.WARNING("Nenhuma chave GEMINI_API_KEY encontrada no arquivo .env. Usando análises estáticas genéricas."))
            return self.generate_static_fallback_analysis(matches)

        domain = "https://statsfut.com"
        confrontos = ""
        for m in matches:
            logo_home = f"{domain}{m.home_team.logo_url}" if m.home_team.logo_url else ""
            logo_away = f"{domain}{m.away_team.logo_url}" if m.away_team.logo_url else ""
            confrontos += f"- {m.home_team.name} vs {m.away_team.name} (ID: {m.id}, LogoCasa: {logo_home}, LogoFora: {logo_away})\n"

        prompt = f"""
Você é um especialista em SEO de futebol e analista esportivo brasileiro de alta performance.
Sua missão é escrever análises táticas completas, longas e muito ricas em informações (cerca de 200 a 250 palavras por jogo) para os confrontos de amanhã da competição: {league_name}.

Os confrontos são:
{confrontos}

INSTRUÇÕES CRÍTICAS DE TORNEIO E CONTEXTO:
- Atenção máxima: A competição analisada é estritamente a {league_name}. É terminantemente PROIBIDO citar qualquer outro torneio como Copa do Brasil, Libertadores, Copa Sul-Americana ou Série A (se a liga for Série B). Os times jogam pela rodada oficial da {league_name}. Fale sobre a corrida por pontos nesta competição específica.

INSTRUÇÕES CRÍTICAS DE DESIGN E ESTRUTURAÇÃO (Siga rigidamente para cada jogo):

1. Cabeçalho de Confronto (H2 Estilizado): Para cada partida, use EXATAMENTE a estrutura de layout de título abaixo (com as logos correspondentes):
<h2 style="color: #2c3e50; border-bottom: 2px solid #2e7d32; padding-bottom: 8px; margin-top: 45px; display: flex; align-items: center; gap: 8px;">
  <img src="[Link da LogoCasa]" width="28" height="28" style="object-fit: contain;" alt="[Time Casa]" />
  <span>[Time Casa] x [Time Fora] | Análise e Estatísticas do Confronto</span>
  <img src="[Link da LogoFora]" width="28" height="28" style="object-fit: contain;" alt="[Time Fora]" />
</h2>

2. Parágrafo Introdutório da Partida:
Escreva de 2 a 3 sentenças de introdução jornalística engajadora explicando o cenário do jogo, a expectativa e a rivalidade do duelo. Use a tag <strong> para destacar termos importantes.

3. Ficha de Tendência e Análise em Caixa de Destaque (Card Premium Otimizado):
Insira este bloco HTML exatamente abaixo do parágrafo introdutório para organizar as informações de forma muito limpa e atraente, sem listas brutas, utilizando parágrafos espaçados e emojis de alto impacto visual:

<div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 25px 0; background-color: #fafafa; font-family: sans-serif; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
  <h3 style="margin-top:0; color: #2e7d32; font-size: 1.15em; font-weight: bold; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 15px; display: flex; align-items: center; gap: 6px;">
    <span>📋 Ficha Técnica & Tendências</span>
  </h3>
  
  <p style="margin: 12px 0; line-height: 1.6;">
    <strong>🔥 Momento Atual das Equipes:</strong> [Detalhe a sequência recente de jogos de cada time, a forma física e o desempenho nos últimos confrontos em 2 a 3 sentenças.]
  </p>
  
  <p style="margin: 12px 0; line-height: 1.6;">
    <strong>🧠 Cenário Tático e Tabela:</strong> [Explique de que maneira a partida afeta a tabela de classificação da {league_name} e as posturas táticas dos treinadores no campo em 2 a 3 sentenças.]
  </p>
  
  <p style="margin: 12px 0; line-height: 1.6;">
    <strong>⚽ Análise de Gols e Cantos (Escanteios):</strong> [Analise detalhadamente a propensão de sair muitos ou poucos gols (focando no comportamento defensivo/ofensivo) e escanteios (analisando cruzamentos, velocidade pelas pontas e volume de finalizações) em 3 a 4 sentenças.]
  </p>
  
  <p style="margin: 12px 0; line-height: 1.6; border-top: 1px solid #f1f5f9; padding-top: 12px; margin-top: 15px;">
    <strong>📊 Histórico Completo:</strong> O retrospecto de confrontos diretos recentes e estatísticas históricas completas estão disponíveis de forma detalhada nas <a href="URL_DO_JOGO" style="color: #2e7d32; font-weight: bold; text-decoration: underline;">estatísticas completas de [Time Casa] x [Time Fora] no StatsFut</a>.
  </p>
</div>

4. SEPARADOR DE JOGO:
Adicione uma linha pontilhada sutil ao final do card de cada partida para separá-la do próximo confronto:
<hr style="border: 0; border-bottom: 1px dashed #cbd5e1; margin: 40px 0;" />

5. REGRAS DE COMPLIANCE DE CONTEÚDO:
- NUNCA use palavras de apostas como "palpites", "tips", "dicas", "apostar", "odds", "probabilidades", "lucro" ou termos similares. O foco é tático, estatístico e informativo.
- NÃO insira nenhum botão verde de CTA ou caixa extra ao final de cada partida. A tabela no topo e o link interno dentro do card já são ideais.
- NÃO use tags markdown (como ** ou __). Use EXCLUSIVAMENTE a tag HTML <strong> para aplicar negrito.
- A URL_DO_JOGO deve seguir este padrão: https://statsfut.com/match/[ID_DO_JOGO]/[SLUG_DO_JOGO]/ (onde ID_DO_JOGO é o ID real fornecido na lista e SLUG_DO_JOGO é o slug baseado no nome dos times, ex: "flamengo-vs-vasco").

Retorne ESTRITAMENTE o código HTML válido gerado, sem marcações markdown ```html e sem textos fora do HTML. Comece direto no H2 do primeiro confronto.
"""

        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                data = r.json()
                html_text = data['candidates'][0]['content']['parts'][0]['text']
                html_text = html_text.replace("```html", "").replace("```", "").strip()
                return html_text
            else:
                self.stderr.write(f"Erro na API do Gemini: {r.text}")
        except Exception as e:
            self.stderr.write(f"Erro ao conectar com o Gemini: {e}")

        return self.generate_static_fallback_analysis(matches)

    def generate_static_fallback_analysis(self, matches):
        """Fallback caso a IA falhe ou não haja chave cadastrada."""
        html = ""
        domain = "https://statsfut.com"
        for m in matches:
            slug = slugify(f"{m.home_team.name}-vs-{m.away_team.name}")
            match_url = f"{domain}/match/{m.id}/{slug}/"
            logo_home = f"{domain}{m.home_team.logo_url}" if m.home_team.logo_url else ""
            logo_away = f"{domain}{m.away_team.logo_url}" if m.away_team.logo_url else ""
            
            img_home = f'<img src="{logo_home}" width="28" height="28" style="object-fit: contain;" alt="{m.home_team.name}" />' if logo_home else ""
            img_away = f'<img src="{logo_away}" width="28" height="28" style="object-fit: contain;" alt="{m.away_team.name}" />' if logo_away else ""

            html += f"""
            <h2 style="color: #2c3e50; border-bottom: 2px solid #2e7d32; padding-bottom: 8px; margin-top: 40px; display: flex; align-items: center; gap: 8px;">
              {img_home}
              <span>{m.home_team.name} x {m.away_team.name} | Análise e Estatísticas do Confronto</span>
              {img_away}
            </h2>
            <p>O confronto de amanhã coloca frente a frente duas equipes com trajetórias distintas na competição. A promessa é de um duelo de fortes nuances táticas, onde cada detalhe fará a diferença no resultado final de noventa minutos em campo.</p>
            
            <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 25px 0; background-color: #fafafa; font-family: sans-serif; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
              <h3 style="margin-top:0; color: #2e7d32; font-size: 1.15em; font-weight: bold; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 15px; display: flex; align-items: center; gap: 6px;">
                <span>📋 Ficha Técnica & Tendências</span>
              </h3>
              <p style="margin: 12px 0; line-height: 1.6;">
                <strong>🔥 Momento Atual das Equipes:</strong> Ambas as equipes vêm de sequências intensas de jogos e buscam se recuperar fisicamente para apresentar o melhor desempenho tático e técnico na rodada de amanhã.
              </p>
              <p style="margin: 12px 0; line-height: 1.6;">
                <strong>🧠 Cenário Tático e Tabela:</strong> A partida é vital para os objetivos de ambos no campeonato, podendo influenciar diretamente na briga pelas primeiras posições da tabela de classificação.
              </p>
              <p style="margin: 12px 0; line-height: 1.6;">
                <strong>⚽ Análise de Gols e Cantos (Escanteios):</strong> Pelo padrão tático das equipes, que buscam explorar bastante as transições e as jogadas de fundo de campo, espera-se uma partida com boa movimentação nas áreas, o que pode resultar em alto volume de finalizações e cobranças de escanteios ao longo do jogo.
              </p>
              <p style="margin: 12px 0; line-height: 1.6; border-top: 1px solid #f1f5f9; padding-top: 12px; margin-top: 15px;">
                <strong>📊 Histórico Completo:</strong> O retrospecto de confrontos diretos recentes e estatísticas históricas completas estão disponíveis nas <a href="{match_url}" style="color: #2e7d32; font-weight: bold; text-decoration: underline;">estatísticas completas de {m.home_team.name} x {m.away_team.name} no StatsFut</a>.
              </p>
            </div>
            <hr style="border: 0; border-bottom: 1px dashed #cbd5e1; margin: 40px 0;" />
            """
        return html

    def assemble_final_html(self, league_name, table_html, html_analysis, target_date):
        """Monta o template HTML final para o Blogger, com imagens e rodapé premium."""
        date_str = target_date.strftime("%d/%m/%Y")
        
        # Lista de imagens de futebol de qualidade para usar como banners no topo dos posts
        banners = [
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgVTkHNL4qdrvhkc9B_UZenCsze-m8bVCA1BOsa1tgWsSOOKBIGTMuMo7rw_FwcY4xHzVosQTX-f7iozW3OuaFwY7IzdPxp7eowhHFRaGyQ8fNfERG3J0kovbqG56_MplclwUAkGVUFqZ1KFyE4CmYTqm5_12gytEkZMRrPHOw08A5NI2CNqhtFlctEtCq7/s1344/img003.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhVZ2FdWVZBkkjhEtStJj0O08OXffDJ9q2-wgsAjrgdk-VbFRwlrg4C7LIfLO65aBZadbuJuhoZ6HOygwf8JgoT0JngS8olxy6QrP3QSlx9tXLvR8nPGtubs1fCo6CJHMqx1py8abnUWIiVPpGB-N9s0WbUWbK2w8LSnSkQlpWuuCf7OWntfcDg3eV_wOSE/s1344/img3.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgpZgEYCwLHAlYK12rYUUlK8FIcBIx4wY2izBNCd1JzvYZXvp7hYH4T9-CJiwg0CtNQEbXnjSngdOx1LCTEe3svxdDhQCWlQiYvBSfvTpnaZm80R9ogC6tWQq5s5EsXrMuGzPs2pwJCMaL7xD1ahyphenhyphenyrtD_wF0BVxMwIM-CkbZlWlbiaasRT4s4E2ax5Jqpd/s1344/img004.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiuBkP4UT2JSvMGvp8573odZ-8rFEVnYDrMwA5Ma16EDYHAVIrFlj8TTOhLtQhs7zvG_ZTY34tDCUv7xHQjESBYGKk22mh5cYhscx1RJInCn2MVYPnxlUaSQe3KpD1W372elzLQLDZSW6JCEct_poxgBsNZe3A2qW_xDgDTB6ytQ2E_LCeXTOI2I1kmq6ZG/s2560/img4.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEirE2QoAAXWa_cCkbDpPMhiAJwJ6VmEPWms9WFAYKz2o34uyRcmqJxkcpztPnDBX0KnJgU0xg-YXePB7jBmRhmPhnQeT8t0dmjOs7aPqUVfmowWd9e713Q4Bc6g8vZvp5U6FR7KkndkQm6L0u7QBqwMdXnf-kqEEKR5kpc6Pt9wbgr61AlYprDQnMJbCcYq/s1344/img005.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhEDq1N0DnrUMJu5N-rUWEc-pZZdJv8fIal8xMXSjnZTy6ZGPYDGDI354zAOsNcpUXMJu_z3xHK55A0llzt5vX8e9K_FP9HgjajZ8AkbydmBYgyyWZTfBC-vd6wpTzpgS0djXAlnENPDxIyzSQ9EyJMJXr1MXSs0wim9VCOM7bR3aUOO8gqPMlJfODCx7l4/s2560/img5.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgLEAv5O-Is0uXe9PbThouz2j_5ezwdzbeO3eTKeRh75Yl975HzOWlruilDLVtXQgqqFp6K_2erxALjiGzVXcrokgL-76VYzMb5O9i6hhS_gD9tBqWO4v_nMEAhAkI8FFE7RHmLjdBBOPWeu1j1nJmd9f4ed18LB1rVRCyzU3_ecxOBeslcD8XoJSZi25ih/s1344/img006.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEi-kglwnT1iMWRHpRXdOwoJmdyZsRXnJ1Xec9D_HSy9mBJ8ZoLYbd2s9kc_ro9DjOYro7_iYQi-HF7wg21my8YmjNIvGDYR20SvioKQZdTtn-8HvaSJGFNrcY4c-NVPfNJXPAK4K8x98o3PSIqLwqZ7OVNYeUwGRhcVfoM2juydPGaDlYWjVpoCCnhQmn7o/s1344/img6.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhxnbknA_X0Q7QKhm11HKkcs0JiP1kAa5gqoD2EjJIWZbIF-pcP-5ZsA4pgca-ROpaGBxhR7TPzzPREKFYtOeDGBYKMujZoJbj7HZ7UQB1SG1SeEmO2s7lAHMAd5n8xUfzIYa-oTLqPeHgp8Tfe4RDYIGUOidu_vElp9DS0V4Efi3qAiKx1kXb7zxC8Vv2f/s1344/img007.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjF1965fC5ORSI31EX2E1EJvhe5zKKrOuKbOJmTQ-s0iYov6rTjlxP1-AFYMey-yAYYJ5BFxVDjyVPXVArY6U8Vb67pLyI7WY5q8bPIBcxwt35Sov5HqiXbtu8FHxpfwE99dNQBjaeux649HCOIKv7DBU7wMRQCMFYhfHvuNGXFzVzmpjoqUFheQau1FfC4/s1344/img7.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgJ9AGRnlepPRsh1XRTW8CzSJYLAISA-E76FCB3dtPufk2m7kYq3uN93OhcoioSriiYwuu_772guCfL9lah3SpsxsqnA4hLay6-UGsPKcku_EuQ_zfN88oDOKkcPHqHBbSIlzSKo-a1-XidkxynHO2zHEnpxhFpLs0G-H2x94UeXchEeUaYjWoyoxtMbkat/s1344/img008.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEj0ftL3H8Wu0yx68F6RlwukHDpE3F5_CSRJ6sYjX_bTTQQJ-XUSKkeq5I5989vrVjtpHHnfG6RylUBMuI-GyTroPjfaKjILigzTAg5aVH0j_bqqqoWoRb9jD9mqYsTM8L9Ch03NyX2QjOnXxuFCGTpIa2OGXoSHY-fvsIYShvYDM8yvzY1h6P01QwS28esT/s1344/img8.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgeyuft_2U7p0fGtGf49vrkTKlEueq4xvEWmbMeWAUZCtzQmyEKq0cqeK99GdfMJC1R9qdZXvc0p-pRjh6_CqRaF9R2jFetur6e9FQq1XGrXEvU7pvkq6p7BW4WXHdCVQav09P7LwGUya73L5gMON8Dyu2clCpzim5YpK38xjPk5aHeh_waVOoy9d8Nvjej/s1344/img009.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgQ-T1_Hi4WVHyxY5b6y4LLWjnQPQJ-8mwwlrYjFhv2cQRPA9WRc4Lic7nGGoSzkG76TLDwbBUfAEJ0NBCedZ94se5IJ4OcLv4C1_ycqnTVBurXD12cUBIug9gXfUzUuaIkUsc-vj0LRd5j8Ews1ZQXh-uStv8v0MOPOl4SjN8R35Wg-RMn6QYtg72HgUMS/s1344/img9.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiX86Sdm6lQ22O1ZX3Lh6CwrN5OAzsc-OeSnahoZpG5GtghmfspMnDYWEQWOLmH9_NVCAowvgSue8VU1BgV68UcwNcyEx2wOM7yeeSOuW-DM5O7Pu8ibTwdyxwvb6CG6LNtPxm_gGa6-I78aelX2qT-Hsu6Pr3hxGAgRhsKFIkhd59DezCVqsLpFWesAcot/s1344/img010.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjlDdsrOFqTjQCSasKX5kgVvQOUOh-f9Dc4ImHyWhyphenhyphen_ANDz5SeAh348FpOcwwTc9EZCd7X56BnnTmxrzAKKQccM5K6uXQyHvK72eAwjGZr9TqsT4nQC4HB_wlHj3jKij8YjPRuI6i0QeFPEaKgN9O7t7c9hwb-GXd-r-hDkmtBl1r_0b_HhtIsDqY5s0YG8/s1344/img10.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiEtdONelQ4SueyR_vxUQWsdrgCdpwVQkYwGxbTvIJOsMbMNx51n4GHdAEUbi2doZgDce7lDYpDR1irxeIdrGervFzb4U15ERK4_IBluhSwae26S8Oh6JOkzRsmm6KhforuQbHJ-cx5tdMAnL1FotqFNYmbB3Sye2FAaTJolU7KTU_zpUQ_FevsjKDpdZcC/s1344/img011.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiad4_MndK9Fy2lHxCW54J1s_3efGG5haRI5Bm0bYdg9qDvEDCjbCYk2EB9USMXZ4Yex56djqbgY_tPLNO27WVyhjhmIFC5m4zn21JJtFD6S6qO08cYPPRKT_B7YeKvIcFbZfaPb8r0rCFUACM_0aujrXH2WIMA7oXV9nQwLw9yk_vmCIS3La2IQ3jqVGct/s1344/img11.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgkv0Heytmaq1AN0FYe71idIQXLa_xCy4l9UGITMFuVOVrBKB2GwwKIGDzrHiZzwfGmc5tFCAQgNNMuCveFkzZFCXbg0vU6YSxmPc22FbjnEHMwuSvpLmmk2elKd59Kq0IKxgrSEszjF4kfo5nLlzqqBFXgRjxa12iTdJoBTAKI_HM-aJLxuDmxl0Fphm51/s1344/img012.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEh1_aeUZKnaeTeyg4Qe6tV5OB6RQkkGoIdWi4XqqnebmfWgkirJnYM9sEbok2eXqaitHqN_waqGzTDLqSOLMHVm3ZOYZy-UyYOi8TISDk-jISa9hz3gndAPhp59lBMbgQVf3R4M0_iXvz0vIsF_3AtiGuY9KI3j4Ljpm7oBjzMqJOADmmWTO5x9C84zBv5p/s1344/img12.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhd-vn0iKYbUbVIJTCJLPn8-x9ri7Yxbulcz-izmcyFslNABMRxCSBO4vlrhyphenhyphen4MwIEP3y79SDNK-IiXt0WwqMflpq9UA1RVKibDZz0qnheXI1VwiQMuVraSE1UGccuHflvRgpOB864XJtSxue9NQBjgibrFu62Edqt_vUNH2eiFoG7gaMbAAcc027WkZiEw/s1344/img013.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgxxFmXKdlYwXJxzA7PU3KFriwrgIHfiijN9X2mtqxtAPkSKfHa4H7jAgTvHYRdqAmBsGAwO7Wcs4xYp7PeWeCLRGUvfwsrvQFjo2fMY3FFbkYZt2OGvv6KHtdw17VjZ8V58z2rfZfeNJEE7h5wu0kB82HYb_8mVaPKDc9hN-997bXcVmdZ_ktuPjvc41Cj/s1344/img13.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhgKZmuXzezl0_9kLWsMGbiOjguyXXQVdCDL7tRTyFcvD-G4DFjDM2wn04zrT_iiU23sUel0yhlBji_A_oSFLQLkTYHCM-pgtG1_t4C8R0CD00ohBoEfFx8JLQYkiQWRaByiUMJqZtf8aVRV1myPFFOALgxLTjB93nSRTw_uSny33zowwyFY2tqhuY1DbPD/s1344/img014.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEi6VbXGyxUAtGOapK49_U-4hVpOGY-6PuzpFpu-taMVDTRb5G6_bOBud7ntYBR9z39Lnbr76S2W8aL9SgFqrIW80vLW8dLbnqBZ4kJbhmaWU-I8Fzn25u3qKOIKIhdst217iZju-xMRymFcMQKN-65jOVZjVnUtcvr5tiLO32PZiTGVXMeSMdw8QLs_JXDk/s1344/img14.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgfjKXkPWotVkBEYS-aHaue1S0a6DB_eSUYc_eQhlF7viTw2VefP00FgsLomahNR4NhKkTCYbj0mBM5YsegArl4BsF7LtUSoa_cxfX8pBmnJw8MH89RSk9D0rZXPKcvvrQrxP9ry_ZX_9pUFdyYX6dGp_NgNo8alu_aDPECIRip_jVsPYPcWLS9w6HCulBQ/s1344/img015.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhBlfAr-We8-embWdET2YEED6AGpz-NnDjQC59TCpm6OeM32KCkg49WE41Z3VqTO_3_jhjGaTtfcGKgiRGAwpBdbvW3oX6NVnhsZgJXRQ4tvTfub-WypdPbBAyLz5jenoQllw2a4mt5sA2_IPBom_tAz6qUrjDG6cijUN-3X4S1DFw8VCzez2ki1Xij00kT/s1344/img15.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEizkuXkP8kSu3hkBV-9J20oivkMoYENNfp9Q2YudYR77HTYNMLxPUfAY3YLiFCLBD0gvT0nptTNwX0axAy3QYr-ysHA-dVbYlZjzeyJMTPdvmclLy8gyG-VLMtU983R_1GDRmQVVm70DEiNoupGL1hriIj8pJ-bbALhvQ8qDiFoN5-YKUE4aVw18_kCKGnJ/s1344/img016.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjroJLGsaxctTU6CMaei62Z1err_GiwSUjE_Wq-QvWqBbLCU41Gv96yKX5RxNOzxJrdJPn763xvRHOlT7XAH18VEMB15xpCzPVY9liUbi9lJho2KPeMhPTH-YkjSWSo5OCUg08u-xuwNU82tfna1LEyiHIUw7BK-wc1J0vAwEjhEkOpVWOEJFz0OH-30NSR/s1344/img16.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEi4zC7r8WzoODkyLN0-OrUn2dkCeaItZaCwY4oUukHybPitEHB3iq3nbcp9HBzDvhZTz-4zSl2aShqJHa3P-8Z7DXZZrLlRHcsdAV_tyNaybcDhrr0DgPZH4TEv5b_rSq4jPkSXy8EHrj1zJ_VWh49O8uk0jSbapZyKS_12JutLPfVjWzsVbGucYfm6xbFr/s1344/img017.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEg_VOazNMgytIwkR0ywLXO-zdP83ShKizoL9rbbj0MGbszcmAc4bhmP3Ho14pjYvdMkaNUWMwA0LBxpVpryhe0fJ-BRTp-6suqn9Hm0OwY5_K8B_pU2CUT742bawYecH_QXb59sT98m9VuffN4zSDPhFyshitl946Z23imAViCeIwMg7TzgCupwDTEX2SsO/s1344/img17.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhcNeFpD8lKYjRNdShnnhqt6vIbEoU8I9LHlpMvTe4XTwrt0iilbpRJNDnxOlPpbTz4ujA2CrFKCWcHciOWb8iH-p8IbEg2wgZfWjSW2ijxeIlzmCgYIN5wg-UBhM-muWRy93W2kXuPik43kPuhYwMEztBrbmKs2iO_vZ7LFqe5TD94ob5kXPUoRdR0Wc2q/s1344/img018.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhgtfNRC4mcrC2KrGNZO-x7Di7IrpaSnhH9W5OGbhLEBxruFiHjuuWw4MBcykbfraytalNMSYtJC4ffbIULIyhsOmPV5ydExSHU1zBm8MMhtSsA2T0sMPLA73vVmy6v0NUZEnPSnClbDNBLIHraLfou9OoVj_g84NokqVmwHgxSJz1q2WUaNy-2OBcT0H9s/s1344/img18.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEi57F0xsQaSZ0Ux3t0eNvW8pZms2g5uvCnEf1Q6z9_eOVEnffJAaZz8EejxE6x2fOR_yJhGMSZJoeJ3Ro2OjWhcxbdZenVbxP50XVWwX7VZpoMIabwpdbKbNxnLQuEbNsU_9Y73j4YgwIdyq_Co-uWosFnYu5UPPCVnE2ekIrk5rMa2ODI3R8lOY0FdpIzm/s1344/img019.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEj6kUj49cYy1FT6rpoEsBNFtdvEDa4qyiWfPSOD0NjzIPwDTLj-sZHRrJkxoZMuQVorSGxp_Am60D1u6usHv4mA-9-_yjmeIxnv_JNXeBOxVPVPfx49687d8nLBQQbu_6j8TMCXLfwpGi6V9wimZfb3vmSFJqJ1Ps87hYXvuKG9Zy5J4BvV3B4hZo4gHijS/s1344/img19.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhcnOghEYrtTBMWs_Og2vwL2LxM7s1vGUFFYshXMVCXEIBZ5PC97pjovfKH3cRNRE-JcOqPbTi2ILEElVw00tkQ1cx4n_5VdD13w9aSWu8W3HhDHWq5N_vDFQ9wqAKSyIhb2RDn2A3dMMQ2dN8BGAkYBZy6ZOvu3dfs_UGkho5aivbbOIle2gFax2FlS5uc/s1344/img020.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhqwZWpifP8DyC7eAloTAjGXM8D0NDzBtqXC407G2N7ZJwUv3C6BOKOjnSiNNVMFcwY45KLsykSCMlPFCb1PL-SqyJEJk0106qUk3pZALHvtkYNNNO14pHuui9sXpCWXVT3c4CYVYzVOkDVLbzs-GqxyvCrkgYPh7FHRFGcuU35V4jrKJ8ywKDmd5Gx5yiV/s1344/img20.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiM_Ybd7nLxqPo0nNlfffdhOEI4XUUh6q0phV1nQlroMMHtbQeGv4_V_FYsniamhnsokQqPVTOh1cvW10tjcTu6PvUa_N3QKM3UCjl953w0lqCLDzYtiElhN8iEfikJ4482bWmvJk9zc0yB2OhZ7GatbXzAFm5ONDrllp5AkpM0l-RwUU0ICI6ffLcP16sK/s1344/img21.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgn-T3HIJDMyv2oft5pFoOaZZTU8r7Do_fBOa9iSCQYlapcaYfXJ5nJeE815CpwAntJeoEx4JVyOK8EMDTHUCwUYUDbb8ZCfvC8NNQ_JTlXP9WNLxrPaDibbihz6-6X3owmevbDumnwpn_ShFLMzEkUvTB-lRE7rBRXl8TraZfwrNRLkW9vHBiQQn9H2iE0/s1344/img22.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEh5SryUIGbbp7NZxp4MKylnp0bx4HyzvqafQyUI71HWoRuKM7Z01eNhUSwblw-Yny6TLgDD5i4RAJ6wwBQmFqMRsckj6pHQ2VxUcdWYP_YkJ7EauquxUr6RM5IZyEWqDzI1QBXbzAnAhDiz8JHEAD9oj-FVY7zXFFiVgarkYQNrnuWYRfymQqJ6fZSysACR/s1344/img23.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgWySN6BvHex8syzch6VnGkzmkFgmhZLI61892nZnGTSXBlWSHL_K6vgfDrHVDK_zaadj-sy5nBk-sQgVslf3_mP12yQ-wU_G3uv79acAGml4nlMMLfE4JlIh9n8KtlShMwdMTjibEye2z_v8QgSAx114pcWQXZ5_zXL3vP-AzaUnU8KAJQnq7Q-YauSkh8/s1344/img24.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiw6herP6gWxau9gWB_Rfs2LlXWLCgY-TKnou_SXueDKN1RyKv0YrNPf1De0sWTCWSwT8J2fV11itua0lN3Dr5c6VP5pXskTVxA6YpVmORb37lwpf5BemFEao4BP7ybpXaa42XaWIGXMM3mrUnkSTxiZPbs6b7bIq5MpaJ3Mc8_69-lWcat6KzgS413dNPV/s1344/img25.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjwgjnE5rMkpqI84FNIYXakCA0bmipy67Hdr2Ch9ARiNYREGFD1rYNP6lMKSZOt2WBChwyX9wHU5I6N5WOObPT8E2_u4cJ4xnCu51i0NDbAysgrQPUYcXKBI5PlHX-pKLD_QdkjdsnMLVzLhsAy_QD1pyXAPRvwgNJDpY9YQ0cEK3dKWU88apxCphD0XiN0/s1344/img26.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiE_p-EYZVLBaoV-zGJnA6u8FNIC33nrBjSQdH0ytl-ycD7UgC0Z7Cr-Id8KGS2BNr94havx7wxp5wX_JDxUtJrB9aAnCkdRRqTTY_fkRqB16zqz2EM5XP4ONvYCxlnwxhE-_y9bb8uxUja2zt88uwchVwQ9qywt5a2TIE5GlnV6tZ7-TMgHmfqv7XLBMVw/s1344/img27.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhqmlyKYMF_1g6dzrGJ2_7PE7oDnXlbnTJeg2dyCOAnL46zRmhqdONETRcB0A2TkFxu2usKgyz_8o9G6s6eNawmKLeGXaZ6J62LXWqL6Y3vm6YdvHlI-R3ic6R_tuQuNLg6IcXhU_DmBMZZ5ztoXK60EMe6J55j9m6AWG5x_vNXuE8XqEqaA8USBw4ZFPCb/s1344/img28.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjwoXMNO5q3WtMGWH8lORtsFQPrzdML5UZ6cV-lJa_BoRZ7qkDB1Cue6gH0n1k2MXbAb7jTB6dtm-Hfk-SFhd60In-LA1jSnSImV0OD7PkrLshzxkCKIYyZ_NUyUKhL0V9fAJdiRqi3gnJjjEU5DOvZpKfuySFdIxTrFXjXZtU-4Pi4Db0ygecpplMHyOCh/s1344/img29.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjMPiuP-0ZG9k_djPOahcWSRJ7RM3t_S50Zi2wVNzzsjgqj65YyaPQ4UNgCsjDtnfE93CthO8YaLWXUEY52hfa2NjKIHqoS5vcegWVRNpbRsjoiuOGokXVyfvR4pg6euByeiR2_WQNeuHpoLEOMa-i5I3DTSshTvd343ybK-Zooq4gsk2NyLmPxMKv02IQf/s1344/img30.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiwRL9bUAp_ebZRYR6PIv5rck7BGV5iJy8w5sDKiUOXpG31GXnQ7IYHJF1d8mNUHx5tyFwHFfnXmQaSRfDJv-bH5bDu0wNGeautBKTRcJh-qEaDzqyhrz5K3wXCRDPoscDT23zeQyn83KyQzlHA0geqPsmhOWgkU-M1vPpXF61G-vK6AbFBasyZdf1SgQbU/s1024/img31.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEj6CKwal1-VmL0VmDsfUVU_rPy-M_vOlAySHJQ20PlvK8nAzuuAKVgSMf7YZwKH6Zbg28RO_A4eJRxHdsb4Q40yl1Fi4m-TnBZ1SSHbythm6tFRsoYFRyeT-tjRN5F9Yxroa7Vacz-gngDMNkU8zSSOm_S2aOXnYDFFqg3WSn3sq9lzpQhg9J1kDdW6j6he/s1024/img32.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhirpBIuhQ5bQU9of-WfXRfukZZypWvm6WFAKEi1PS4U1WTv4d_9m1ZlqA5mOVbdEht5qgnkP0shzH5G5Wfn-rw6LLEqIozoJz19Rh7SlcZm__srngBaJ83PTKzg91Te3tJRxhc0I4F9ckapwQ1FLshOnI2ot-LgpcszBMdyQylOdX9wS_3fLm36x5HjibR/s1024/img33.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgyFruzLVJYWC9nsXWrPv4TFBPaTozeHSO_qEmNZZEvCV-l60t5akSTmX8l-aNisH3F1xa_P7R9xdnSawGyzHS7OK0qKNwwwW4upzlkCgHlR4M37gPQHcjimp2gK2fNK-VwDhj5y7cNOzSGWwaPu4_J2wF4YfAs8Y8UoZzyE_kwPKRHXohQ9zws47-A7tBK/s1024/img34.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhBj6OaQ7BtEV2ZyDouRvRH2TWMDa6YfKktmx2bxdZ8z1_0tZ66k8YtnbJFu9_O0AiRmlzXN5eG4Xgx-dQzth0S6FXm9Taq3_8NWmGtDc9XTESwesD1uyWBGYS42zDIlWBhp_m1I3LbmB8gqA85VV-V924lsI0R_YbIYp4ir88yUh5ljAMTZghwZMyXIb6r/s1024/img35.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjWa57T8tZzwIv4nXaOYvqEREZ01OFZ0jUYdzr8fAVUMWsCB4KMo3TIrHgWq9DPXbV8n6ZzL2kE-f7bqNanX3oreDv6QfeTHGnUYcETBYZR9BGnk_HtYEhdGdep1nC17S-qgHcujoNtRl_rGCJcLIUEince_aLKHjpIIqkNdyt4ueDy1vnJu6oqpyNDH7F-/s1024/img36.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjsKMWRGqECH6sZ0ZkF4kqhErEkC2Oyk-zEIcdeNimLyaHOhtojsgX1ad852zfRmhjzMM19uw-1Xio9Oo_DEKgEWukMfBKSIBnsmLsWDAw44ULer_RBw0FKJspaDsTYnxs21_CheSBCxpqqqdhwccbN9tx2_KyoP6OeN3gc4tcvJEuVd5nAhinO78QekRfP/s1024/img37.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEh_7wFzMXaAGESHtg1YeRV65tN-ciCxmGcJdk4uL62bzGWnVTd4TjQToN5EnH8TQvLJDuvS0Eno3sIgPwgFSnsQZAqHIDOeRfoz_SXvbcdulz0IDW3hhaRFJeI654ci3ezBeLFfj47DCu3PWFE1gC5UVdLnyPpOs7EvCLcgGsdQirNeXWQ688MwvoiHLgYQ/s1024/img38.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEi42SUD87dIMRaB01zt7QdSocJkSiWwVxJoiv6TvG3AgvGf4OQYf3B3d1thM5WIB4UpwshK8aRsK99DN6hFB4fDaloYdcG3G78j5IJvTEyvQ1NkifjXiIQgyHhd20RZVrlejx9bA8W1Vy8WmMPwCUxmzu7fg83PXzcB7Yh_8DUUGCJCoa9ytqUD9vd9hhUs/s1024/img39.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhZItIhpLafoxTgNga_D27SklB_D7EB8rn8Hce72lOQkP2cAN4Z8hZZ2H9BsPANEqYWrSP45bqVkfcaUfHmM9U7cWAvu97-nHrpfjCNJQws1CaSjcE4cY9eOQeaYGIaVI4BzJ2kWeD5KsEGWSsR6DsW4Vkb-Vmdw3NEkwsZRrPBhLWJe2qPEm3UdX6jQ0F8/s1024/img40.jpg",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEg1pHBIIXVN4_495qNS_1kbLKJtAYDWnu5BsY4GEs3VO2YOIuX1R0L31vcRV4RWtpj5t0j-QBGdQuTQzITu9FO5mppuqZdRlQXPdntFVo9rovXaiSA7EbcsXmCZcdy5TIMMly6oVP8WiZ1etqamNhJ77hELjwzoS1xVePz_u6hTh_VGH9ZUssKGcBSAAjFD/s1024/001_fundo_estadio_voleio.png",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiKa2UD-9SicH_C9GvoymUnXDbGgR2m1QSVPVlfEuxYBDmwKXl0eFD5yoE1bE9eVTrycNxw7KjFhL1XmSYVpeqgT2DN97aOIZPF6FnX3fnlUlfBHz0yqmOE6jtDBxCymwNCiCB-X5mcv2UKFKbR8v7osO1Z5dmNT-8vHATQNXywZNsvsaPOrBkRBvbRCdV9/s1024/002_fundo_estadio_comemoracao.png",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgdwMq-BIaJ77jQxxgNP-9aCDYeqVhmyz0V0MROAhXgTSDKTa3uCFyEKru2uoXBXOdGQibhFuOhSyge1KA33pcSNL-IR-7F1KkoKjkMct_lZwRBm1rm0xHKCGz2A6euw8aDXGOd_GFT_Xw8fL5xXMLb5-443ex8LRkCwkN45OhFkVIBSkBRNln6lNYLnM51/s1024/003_fundo_estadio_goleiro.png",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgnrfocT3Wr0refI0Y8-cz5zXJpYWEm3MGTC8OeShjzkbQBZHkHcdQlGlrhqpbSFYIKSf28eEeQ7MALEn2LZDgCfwoh8p7VFpYb8zhIBZ2HFmzvGkLGcizY3KSQKetgHtC6oxq4rcam-Tp-yKM9O5ZhLPj0ohU4sVCl2FAEldWXfEGJ5Y3rdIEuntPUK0Pz/s1024/004_fundo_estadio_carrinho.png",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhsGEzLCMa3orPDRNjD0hT1RXlgnFSZlleZrXwbzEi41rzzFTSZ-naDNEtlX54tIMZ8Yn1_IB3FgUj011tqsMvcarzf7vnHHIiW7lwShz-CiBNTvqrqTTiPxvK2eU-In3mRJfUSvL7ew-ezudUU3EivuUcz6M8lnvpfscLLFsNCMc2OFBadsH1-81B_IZsS/s1024/005_fundo_estadio_cartao_vermelho.png",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgWMY_ZU_rnBswDcyCxykdWOGWvdBqLWtGDLo3jESBfthEUYI6fLRJ_2nOMgi5eXX_PySE2OsbVDBcUm-OlWLZ81RkGp9RpX7XaaMY-G54RXkwD-w5TAUO-Zyv7P-G-HK7tzt4s7igLVSbkV9byq1esRm67EjMo6k0gIZokMASq1TYapsq4eSE4_Z6owoal/s1024/006_fundo_estadio_chute_angulo.png",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjG-idCrRnWMALAorWf9LGtFeeh6qSRVP4l20eI7HqJkB_819IDCpA6NbmvFi38LX9O7Fo6weeo0f4mzdma-n2uxDABeLUgmF-fRgUdyrMrJcMFGEykBemVJjN0u6smxSlkP4tGCiqiXjlZdShshcG2CCWTZlAP73G9jx4OutsVR3idRc6ZIf90nH76kXLj/s1024/007_fundo_estadio_torcida_bandeira.png",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgQ7thKHWZow_daMPskY5HbU_5aW5T5VIiTCEDz5NpIlH_8vGuA9T4tVw4EJMUtWz8xCO6J38ajgGm6NZPpn1HplgVeMmECCrPqPKJLvQxp5znpwdmGmj5hcTEtr51L7yyO4l6-JwLVMK-ZwSq2eVQdRy3NlwJfOrHiAEIQQUvG0zKUraIieRm61cOQOzWn/s1024/008_fundo_estadio_tecnico_gritando.png",
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjeIvPtxK_VZkgYnxEY5Lqhn085zFMlXufhAe9s9pg6kSndHYRtq-aqSO9oNY1areDp-ho8PfhBItQjSRns8atWhlmKLuK7WwO3FbmYzHVqBz4AuiDm8H7uOxZQazFRp5Xkm-2Ezn7-uW6vmUIMUwV_6AC6Nwtcx5Vu7bYDzqGGCdwaZVlJ-XnJqnpM",
        ]
        image_url = random.choice(banners)

        intro = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; font-size: 16px; color: #333;">
            <div style="margin-bottom: 25px; overflow: hidden;">
                <img src="{image_url}" alt="Cronograma da Rodada {league_name}" style="float: right; width: 300px; max-width: 40%; height: auto; border-radius: 8px; margin-left: 20px; margin-bottom: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
                <p style="margin-top: 0;">Amanhã, dia <strong>{date_str}</strong>, teremos mais uma rodada fundamental pela disputa do <strong>{league_name}</strong>. Nossa equipe de inteligência e análise tática mergulhou fundo nos dados para reunir as informações estatísticas mais relevantes dos confrontos, com o objetivo principal de ajudar você a entender todo o contexto técnico, físico e emocional que envolve cada equipe neste momento crucial do campeonato.</p>
                <p>O futebol moderno exige cada vez mais leitura de jogo. Por isso, utilizando nosso banco de dados atualizado em tempo real e nossos algoritmos matemáticos exclusivos, preparamos uma prévia completa para te orientar no andamento de cada partida. Analisamos minuciosamente o desempenho defensivo, a eficiência no ataque, o volume de escanteios e as tendências de posse de bola.</p>
                <p>Nesta rodada, as equipes entram em campo sabendo que cada ponto conquistado ou perdido pode redefinir o futuro da temporada. Acompanhe a seguir a nossa leitura tática e prepare-se para mais um dia de muito futebol e alto nível de disputa no gramado.</p>
            </div>
            
            <h2 style="color: #2c3e50; border-bottom: 2px solid #2e7d32; padding-bottom: 8px; margin-top: 30px;">📅 Cronograma dos Jogos de Amanhã</h2>
            <p style="margin-top: 5px;">Confira a tabela com as partidas da rodada, horários de Brasília e links rápidos para acessar as estatísticas completas:</p>
            {table_html}
            
            <h2 style="color: #2c3e50; border-bottom: 2px solid #2e7d32; padding-bottom: 8px; margin-top: 30px;">🔍 Análise Detalhada dos Confrontos em Destaque</h2>
            <p>Abaixo, detalhamos o comportamento tático das partidas mais importantes e movimentadas da rodada:</p>
        """

        footer = f"""
            <hr style="border: 0; border-bottom: 1px solid #ddd; margin: 40px 0;"/>
            
            <div style='background-color: #fff8e1; border-left: 6px solid #ffb300; padding: 15px; margin: 25px 0; border-radius: 4px;'>
                <h4 style='margin-top: 0; color: #b78103; font-size: 1.25em;'>🔐 Análise Completa de Gols e Escanteios</h4>
                <p style='margin: 0; font-size: 0.95em; color: #555;'>A preparação para a rodada exige dados precisos. Os <strong>bilhetes combinados estruturados</strong> de hoje (incluindo as Duplas de Gols, Triplas de Cantos e Sistemas Trixie) já estão processados pelo nosso algoritmo e são exclusivos do nosso plano premium no painel. O robô gerou as melhores oportunidades e elas estão disponíveis somente no site oficial.</p>
            </div>
            
            <div style='background-color: #e8f5e9; padding: 25px; border-left: 6px solid #2e7d32; border-radius: 4px; margin-top: 20px;'>
                <h3 style='margin-top:0; color: #1b5e20; font-size: 1.3em;'>📊 Quer ver todos os bilhetes prontos e estatísticas ao vivo?</h3>
                <p style='font-size: 1.05em; color: #333;'>Ao acessar o StatsFut, você ganha acesso instantâneo a um arsenal de ferramentas profissionais:</p>
                
                <ul style='list-style-type: none; padding-left: 10px; margin-bottom: 20px;'>
                  <li style='margin-bottom: 10px; color: #333;'>&rsaquo; <strong>Bilhetes Prontos:</strong> Combinações otimizadas matematicamente para maximizar o seu ganho;</li>
                  <li style='margin-bottom: 10px; color: #333;'>&rsaquo; <strong>Gráficos ao Vivo:</strong> Linhas de gols e cantos (escanteios) atualizadas em tempo real;</li>
                  <li style='margin-bottom: 10px; color: #333;'>&rsaquo; <strong>Alertas de Valor:</strong> Notificações inteligentes enviadas direto no seu painel or Telegram;</li>
                  <li style='margin-bottom: 10px; color: #333;'>&rsaquo; <strong>Estatísticas Avançadas:</strong> Banco de dados completo de ligas pelo mundo todo.</li>
                </ul>
                
                <p style='margin-bottom: 0; text-align: center;'>
                  <a href='https://statsfut.com/' target='_blank' style='background-color: #2e7d32; color: white; padding: 14px 24px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 1.15em; box-shadow: 0 4px 6px rgba(46, 125, 50, 0.3); transition: background-color 0.3s;'>
                    Acessar Painel StatsFut Completo 🚀
                  </a>
                </p>
            </div>
        </div>
        """

        return f"{intro}\n{html_analysis}\n{footer}"

