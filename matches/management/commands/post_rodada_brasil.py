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

from matches.models import Match


class Command(BaseCommand):
    help = "Busca jogos do Brasileirão Série A e B de amanhã, gera artigos de análise com IA e publica no statsfutbrasil."

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
        # Filtramos por nomes conhecidos de ligas no banco de dados
        matches = Match.objects.filter(
            date__date=target_date,
            league__name__icontains="Série"
        ).filter(
            league__country="Brasil"
        ).select_related("league", "home_team", "away_team")

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
            
            # Gerar conteúdo via Gemini
            title = f"Guia da Rodada {league_name}: Análise Completa de amanhã ({target_date.strftime('%d/%m/%Y')})"
            html_analysis = self.generate_analysis_via_gemini(league_name, league_matches)
            
            if not html_analysis:
                self.stderr.write(f"Falha ao gerar conteúdo para {league_name}. Pulando...")
                continue

            # Montar template final de post
            html_content = self.assemble_final_html(league_name, league_matches, html_analysis, target_date)

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
                # ID do blogspot statsfutbrasil.blogspot.com
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

    def generate_analysis_via_gemini(self, league_name, matches):
        """Usa a API do Gemini para gerar uma análise contextual robusta por partida."""
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            self.stdout.write(self.style.WARNING("Nenhuma chave GEMINI_API_KEY encontrada no arquivo .env. Usando análises estáticas genéricas."))
            return self.generate_static_fallback_analysis(matches)

        # Montar lista de confrontos para enviar no prompt
        confrontos = ""
        for m in matches:
            confrontos += f"- {m.home_team.name} vs {m.away_team.name} (ID do jogo: {m.id})\n"

        prompt = f"""
Você é um especialista em SEO de alto nível e jornalista esportivo brasileiro especializado em estatísticas de futebol.
Sua missão é escrever uma prévia de rodada extremamente otimizada para SEO para as partidas de amanhã da competição: {league_name}.

Os confrontos são:
{confrontos}

INSTRUÇÕES CRÍTICAS DE SEO E ESCRITA:
1. Títulos das Seções (H3): Para cada partida, use EXATAMENTE a estrutura de título a seguir para atrair buscas orgânicas de interesse:
<h3>⚽ [Nome do Time Casa] x [Nome do Time Fora] | Estatísticas, Histórico e Análise do Confronto</h3>

2. Palavras-Chave no Texto: Escreva um parágrafo analítico de 90 a 110 palavras para cada jogo. O texto deve conter naturalmente palavras-chave de alto tráfego como: "estatísticas de [Nome do Time Casa] x [Nome do Time Fora]", "histórico de confrontos", "desempenho recente", "escalação" ou "tabela de classificação". Coloque termos importantes e os nomes dos times em negrito usando a tag <strong>.

3. Links Internos (SEO Link Building): Dentro do próprio parágrafo de cada partida, insira naturalmente um link em formato de hipertexto (texto âncora) apontando para a página do jogo no StatsFut.
Exemplo de encaixe de link: "...como apontam as <a href='URL_DO_JOGO'>estatísticas completas de [Nome do Time Casa] x [Nome do Time Fora] no StatsFut</a>, a equipe da casa..."
*Nota: A URL_DO_JOGO deve seguir a estrutura: https://statsfut.com/match/[ID_DO_JOGO]/[SLUG_DO_JOGO]/ (onde ID_DO_JOGO é o ID real fornecido na lista e SLUG_DO_JOGO é o slug baseado no nome dos times, ex: "flamengo-vs-vasco").

4. COMPLIANCE DE CONTEÚDO (CRÍTICO): Este é um blog informativo de análise de dados. É terminantemente PROIBIDO usar palavras como "palpites", "tips", "dicas", "apostar", "lucro", "dinheiro" ou termos de aposta direta. Foque nas estatísticas, tática e comportamento em campo das equipes.

5. Botão de Chamada para Ação (CTA) adicional: Logo abaixo do parágrafo de cada jogo, adicione este botão exatamente:
<div style='margin: 15px 0 30px 0;'><a href='URL_DO_JOGO' style='background-color: #2e7d32; color: white; padding: 12px 20px; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 0.95em;'>Análise Estatística Completa no StatsFut 🚀</a></div>

6. Formato de Saída: Retorne ESTRITAMENTE o código HTML válido. Não use blocos de marcação de código do tipo ```html ou comentários adicionais. Comece a resposta direto no primeiro H3.
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
                # Limpa tags markdown indesejadas se a IA ignorar a ordem
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
        for m in matches:
            slug = slugify(f"{m.home_team.name}-vs-{m.away_team.name}")
            html += f"<h3>⚽ {m.home_team.name} vs {m.away_team.name}</h3>"
            html += f"<p>Confronto importante pela rodada da competição. Ambas as equipes entram em campo em busca de pontos essenciais na tabela de classificação. O retrospecto das últimas rodadas aponta para um duelo equilibrado e de forte apelo estratégico. As médias de desempenho das equipes em casa e fora sugerem números interessantes que valem a pena acompanhar.</p>"
            html += f"<div style='margin: 15px 0 25px 0;'><a href='https://statsfut.com/match/{m.id}/{slug}/' style='background-color: #2e7d32; color: white; padding: 12px 20px; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 0.95em;'>Ver Estatísticas Completas no StatsFut 🚀</a></div>"
        return html

    def assemble_final_html(self, league_name, matches, html_analysis, target_date):
        """Monta o template HTML final para o Blogger, com imagens e rodapé premium."""
        date_str = target_date.strftime("%d/%m/%Y")
        
        # Lista de imagens de futebol de qualidade para usar como banners no topo dos posts
        banners = [
            "https://images.unsplash.com/photo-1529900748604-07564a03e7a6?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1552667466-07770ae110d0?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1543351611-58f69d7c1781?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1510566337590-2fc1f21d0faa?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1551958219-acbc608c6377?auto=format&fit=crop&w=800&q=80"
        ]
        image_url = random.choice(banners)

        intro = f"""
        <p>Preparamos uma análise completa e detalhada para a rodada de amanhã, dia <strong>{date_str}</strong>, válida pelo <strong>{league_name}</strong>. Nossa inteligência artificial e nosso banco de dados compilaram o histórico recente, confrontos diretos e médias para trazer um panorama tático do que esperar das equipes em campo.</p>
        <p><img src="{image_url}" alt="Prognósticos do {league_name}" style="width: 100%; max-width: 600px; height: auto; border-radius: 8px; margin: 15px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" /></p>
        """

        footer = f"""
        <hr/>
        <div style="background-color: #e8f5e9; padding: 20px; border-left: 6px solid #2e7d32; border-radius: 4px; margin-top: 30px;">
            <h3 style="margin-top:0; color: #1b5e20;">📊 Quer ir além e analisar estatísticas em tempo real?</h3>
            <p>O <strong>StatsFut</strong> analisa mais de 50 ligas ao redor do mundo de forma matemática e imparcial. Ao entrar na nossa plataforma oficial, você tem acesso a:</p>
            <ul>
                <li><strong>Média Avançada de Escanteios:</strong> Descubra a tendência de cantos da partida;</li>
                <li><strong>Porcentagem de Ambas Marcam e Gols:</strong> Modelagem quantitativa precisa;</li>
                <li><strong>Bilhetes Prontos:</strong> Sugestões montadas diariamente pelo sistema;</li>
                <li><strong>Gráficos ao Vivo:</strong> Desempenho e pressão das equipes em tempo real.</li>
            </ul>
            <p style="margin-bottom: 0; margin-top: 15px;">
                <a href="https://statsfut.com" style="background-color: #2e7d32; color: white; padding: 12px 22px; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 1.15em;">Acessar Plataforma StatsFut Completa 🚀</a>
            </p>
        </div>
        """

        return f"{intro}\n{html_analysis}\n{footer}"
