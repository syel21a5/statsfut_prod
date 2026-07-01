import os
import random
import requests
import time
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
    help = "Busca os top 12 jogos do Brasil de amanhã, gera artigos de análise com IA focados em um único jogo, e agenda postagens com intervalo de 1h."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, default=None, help="Data alvo no formato AAAA-MM-DD")
        parser.add_argument("--test-run", action="store_true", help="Apenas exibe o HTML no terminal")
        parser.add_argument("--days-ahead", type=int, default=1, help="Quantos dias no futuro buscar (Padrão: 1 para SEO e Dados Frescos)")

    def handle(self, *args, **options):
        br_tz = ZoneInfo("America/Sao_Paulo")
        now_br = timezone.now().astimezone(br_tz)
        
        if options["date"]:
            try:
                target_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                self.stderr.write("Formato de data inválido. Use AAAA-MM-DD.")
                return
        else:
            target_date = (now_br + timedelta(days=options["days_ahead"])).date()

        start_of_day = datetime.combine(target_date, datetime.min.time(), tzinfo=br_tz)
        end_of_day = datetime.combine(target_date, datetime.max.time(), tzinfo=br_tz)

        matches = list(Match.objects.filter(
            date__range=(start_of_day, end_of_day),
            league__name__in=["Brasileirão Série A", "Brasileirão Série B", "Brasileirão Série C", "Série A", "Série B", "Série C", "Serie A", "Serie B", "Serie C"]
        ).filter(
            league__country__in=["Brasil", "Brazil"]
        ).select_related("league", "home_team", "away_team"))

        if not matches:
            # Fallback
            matches = list(Match.objects.filter(
                date__date=target_date,
                league__name__icontains="Série",
                league__country="Brasil"
            ).select_related("league", "home_team", "away_team"))

        if not matches:
            self.stdout.write(self.style.WARNING(f"Nenhum jogo encontrado para {target_date}."))
            return

        # Calcular pontuação para ranking
        def get_match_score(match):
            score = 0
            if "Série A" in match.league.name:
                score += 1000
            elif "Série B" in match.league.name:
                score += 500
            elif "Série C" in match.league.name:
                score += 100

            home_standing = LeagueStanding.objects.filter(league=match.league, team=match.home_team).first()
            away_standing = LeagueStanding.objects.filter(league=match.league, team=match.away_team).first()
            
            if home_standing: score += home_standing.points
            if away_standing: score += away_standing.points
            
            return score

        matches.sort(key=get_match_score, reverse=True)
        top_matches = matches[:12]

        self.stdout.write(f"Encontrados {len(matches)} jogos. Selecionando os {len(top_matches)} mais importantes.")

        blogger_service = None
        if not options["test_run"]:
            blogger_service = self.get_blogger_service()

        # Configurar horário inicial: AGORA (Para dar tempo do Google Indexar)
        base_published_time = now_br

        for i, match in enumerate(top_matches):
            publish_time = base_published_time + timedelta(hours=i)
            publish_time_str = publish_time.isoformat()
            
            t_home, t_away = match.home_team.name, match.away_team.name
            league_name = match.league.name
            title = f"{t_home} x {t_away}: Análise, Estatísticas e Prognóstico - {league_name}"

            self.stdout.write(f"\nProcessando [{i+1}/{len(top_matches)}] {title} para as {publish_time.strftime('%H:%M')}")

            html_analysis = self.generate_single_match_analysis(match)
            if not html_analysis:
                continue

            html_content = self.assemble_single_html(match, html_analysis, target_date)

            if options["test_run"]:
                self.stdout.write(f"Publicação programada para: {publish_time_str}")
                self.stdout.write(html_content[:500] + "...\n")
            else:
                blog_id = "6808698508164581615"
                body = {
                    "kind": "blogger#post",
                    "blog": {"id": blog_id},
                    "title": title,
                    "content": html_content,
                    "labels": [league_name, "Análise Individual", "Estatísticas de Futebol", t_home, t_away],
                    "published": publish_time_str
                }

                try:
                    post = blogger_service.posts().insert(blogId=blog_id, body=body).execute()
                    self.stdout.write(self.style.SUCCESS(f"Post Agendado! URL: {post.get('url')}"))
                except Exception as e:
                    self.stderr.write(f"Erro no Blogger: {e}")
                
                # Pausa para não estourar o limite de 15 RPM do Gemini
                time.sleep(6)

    def get_blogger_service(self):
        """Gerencia o fluxo de token e retorna o cliente de serviço da API do Blogger."""
        scopes = ["https://www.googleapis.com/auth/blogger"]
        token_path = os.path.join(settings.BASE_DIR, "token_statsfutbrasil.json")
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

    def generate_single_match_analysis(self, match):
        from matches.models import LeagueStanding
        # Buscar posições na tabela
        t_home = match.home_team.name
        t_away = match.away_team.name
        league_name = match.league.name

        home_st = LeagueStanding.objects.filter(league=match.league, team=match.home_team).first()
        away_st = LeagueStanding.objects.filter(league=match.league, team=match.away_team).first()

        st_info = ""
        if home_st and away_st:
            st_info = f"{t_home} está na posição {home_st.position} com {home_st.points} pontos. {t_away} está na posição {away_st.position} com {away_st.points} pontos."

        prompt = f"""
Você é um Especialista em Análise Tática de Futebol e Apostas Esportivas.
Crie um 'Super Post' longo de no mínimo 600 palavras sobre o jogo {t_home} vs {t_away} pela competição {league_name}.

Contexto da Classificação:
{st_info}

REGRAS OBRIGATÓRIAS:
1. Escreva 4 parágrafos detalhados e aprofundados.
2. Use OBRIGATORIAMENTE os seguintes intertítulos em formato HTML <h2>:
   - <h2>Momento das Equipes e Importância do Jogo</h2>
   - <h2>A Batalha Tática e Escalações Prováveis</h2>
   - <h2>Retrospecto e Estatísticas Recentes</h2>
   - <h2>Palpites e Tendências de Gols</h2>
3. Inclua a seguinte frase com link no meio do texto exatamente como está:
<p>Confira todas as <a href="https://statsfut.com/match/{match.id}/{t_home.lower().replace(' ', '-')}-vs-{t_away.lower().replace(' ', '-')}/" style="color: #2e7d32; font-weight: bold; text-decoration: underline;">estatísticas completas de {t_home} x {t_away} ao vivo no StatsFut</a>.</p>
4. Sempre que você quiser destacar uma lista de pontos-chave, dicas ou palpites (em QUALQUER tópico), você OBRIGATORIAMENTE deve usar uma das 3 caixas elegantes abaixo para não ficar repetitivo. Escolha a que mais combina com o assunto:

Modelo 1 (Azul - Ideal para Palpites e Análises Frias):
<div style='background-color: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin: 20px 0;'>
  <h3 style='margin-top: 0; color: #2980b9; font-size: 1.1em;'>💡 [SEU TÍTULO AQUI]:</h3>
  <ul style='margin-bottom: 0;'><li><strong>[Destaque]:</strong> [Explicação]</li></ul>
</div>

Modelo 2 (Verde - Ideal para Pontos Fortes, Vantagens ou Táticas):
<div style='background-color: #fafafa; border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 20px 0;'>
  <h3 style='margin-top: 0; color: #2e7d32; font-size: 1.1em;'>📌 [SEU TÍTULO AQUI]:</h3>
  <ul style='margin-bottom: 0;'><li><strong>[Destaque]:</strong> [Explicação]</li></ul>
</div>

Modelo 3 (Laranja/Amarelo - Ideal para Alertas, Tendências Críticas ou Fraquezas):
<div style='background-color: #fff8e1; border-left: 6px solid #ffb300; padding: 15px; margin: 20px 0; border-radius: 4px;'>
  <h3 style='margin-top: 0; color: #b78103; font-size: 1.1em;'>⚠️ [SEU TÍTULO AQUI]:</h3>
  <ul style='margin-bottom: 0;'><li><strong>[Destaque]:</strong> [Explicação]</li></ul>
</div>

* ATENÇÃO: Use pelo menos 2 desses modelos diferentes de caixas ao longo do artigo!
5. Destaque termos técnicos, nomes de jogadores importantes e conceitos-chave usando OBRIGATORIAMENTE a tag <strong> para facilitar a leitura dinâmica (exemplo: <strong>time decay</strong>).
6. Não inclua introduções ou despedidas como 'Aqui está o post'. Devolva APENAS o HTML puro com <p>, <h2>, <strong> e <div>.
"""

        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {deepseek_api_key}"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Você é um Especialista em Análise Tática de Futebol."},
                {"role": "user", "content": prompt}
            ]
        }

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                data = r.json()
                html_text = data["choices"][0]["message"]["content"]
                return html_text.replace("```html", "").replace("```", "").strip()
            else:
                self.stderr.write(f"Erro na API do DeepSeek: {r.text}")
        except Exception as e:
            self.stderr.write(f"Erro ao conectar com o DeepSeek: {e}")

        return self.generate_static_fallback_single(match)

    def generate_static_fallback_single(self, match):
        domain = "https://statsfut.com"
        slug = slugify(f"{match.home_team.name}-vs-{match.away_team.name}")
        match_url = f"{domain}/match/{match.id}/{slug}/"

        return f"""
        <p>Um dos confrontos mais aguardados da rodada coloca frente a frente duas grandes equipes do <strong>{match.league.name}</strong>. {match.home_team.name} e {match.away_team.name} buscam consolidar sua posição na tabela. Historicamente, jogos entre estas camisas apresentam alta intensidade.</p>
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 25px 0; background-color: #fafafa; font-family: sans-serif; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
          <h3 style="margin-top:0; color: #2e7d32; font-size: 1.15em; font-weight: bold; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 15px;">📋 Ficha Técnica & Tendências</h3>
          <p style="margin: 12px 0; line-height: 1.6;"><strong>🔥 Momento Atual:</strong> Ambas as equipes se preparam intensamente para superar seus últimos resultados.</p>
          <p style="margin: 12px 0; line-height: 1.6;"><strong>🧠 Cenário Tático:</strong> Jogo crucial para as pretensões de ambos na {match.league.name}.</p>
          <p style="margin: 12px 0; line-height: 1.6; border-top: 1px solid #f1f5f9; padding-top: 12px; margin-top: 15px;">
            <strong>📊 Histórico Completo:</strong> Veja todos os confrontos diretos recentes nas <a href="{match_url}" style="color: #2e7d32; font-weight: bold; text-decoration: underline;">estatísticas completas de {match.home_team.name} x {match.away_team.name} no StatsFut</a>.
          </p>
        </div>
        """

    def assemble_single_html(self, match, html_analysis, target_date):
        date_str = target_date.strftime("%d/%m/%Y")
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

        domain = "https://statsfut.com"
        logo_home = f"{domain}{match.home_team.logo_url}" if match.home_team.logo_url else ""
        logo_away = f"{domain}{match.away_team.logo_url}" if match.away_team.logo_url else ""
        
        img_h = f'<img src="{logo_home}" width="24" height="24" style="object-fit: contain; vertical-align: middle; margin-right: 5px;" />' if logo_home else ""
        img_a = f'<img src="{logo_away}" width="24" height="24" style="object-fit: contain; vertical-align: middle; margin-left: 5px;" />' if logo_away else ""

        # Estilização: Aplicando exatamente o modelo HTML enviado pelo usuário
        styled_html = html_analysis.replace('<h2>', '<h2 style="color: #2c3e50; border-bottom: 2px solid #2e7d32; padding-bottom: 8px; margin-top: 30px;">🎯 ')
        styled_html = styled_html.replace('<ul>', '<ul style="margin-bottom: 24px; padding-left: 20px;">')

        intro = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; font-size: 16px; color: #333;">
            <div style="margin-bottom: 25px; overflow: hidden;">
                <img src="{image_url}" alt="Análise de {match.home_team.name} x {match.away_team.name}" style="float: right; width: 350px; max-width: 45%; height: auto; border-radius: 8px; margin-left: 20px; margin-bottom: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
                <h1 style="color: #1e293b; font-size: 1.8em; margin-top: 0;">{img_h}{match.home_team.name} x {match.away_team.name}{img_a}</h1>
                <p>Neste dia {date_str}, as atenções se voltam para o aguardado duelo entre {match.home_team.name} e {match.away_team.name}, em partida válida pela disputa da {match.league.name}. Nossa equipe de inteligência e análise tática mergulhou fundo nos dados para reunir as estatísticas mais relevantes deste confronto específico, com o objetivo principal de ajudar você a entender todo o contexto técnico, físico e emocional que envolve ambas as equipes.</p>
                <p>O futebol moderno exige leitura de jogo apurada. Por isso, utilizando nosso banco de dados em tempo real e nossos algoritmos matemáticos exclusivos, preparamos esta análise completa. Avaliamos minuciosamente o desempenho defensivo, a eficiência no ataque e o volume de escanteios (cantos) gerado pelas equipes ao longo do torneio.</p>
            </div>
            {styled_html}
        """

        footer = f"""
            <hr style="border: 0; border-bottom: 1px solid #ddd; margin: 40px 0;"/>
            
            <div style='background-color: #fff8e1; border-left: 6px solid #ffb300; padding: 15px; margin: 25px 0; border-radius: 4px;'>
                <h4 style='margin-top: 0; color: #b78103; font-size: 1.25em;'>🔐 Prognósticos de Gols e Escanteios para este Jogo</h4>
                <p style='margin: 0; font-size: 0.95em; color: #555;'>A preparação exige dados precisos. Os <strong>bilhetes estruturados</strong> para {match.home_team.name} x {match.away_team.name} (incluindo as Duplas de Gols e Triplas de Cantos) já estão processados pelo nosso algoritmo e são exclusivos do nosso plano premium no painel.</p>
            </div>
            
            <div style='background-color: #e8f5e9; padding: 25px; border-left: 6px solid #2e7d32; border-radius: 4px; margin-top: 20px;'>
                <h3 style='margin-top:0; color: #1b5e20; font-size: 1.3em;'>📊 Quer ver todos os bilhetes prontos e estatísticas ao vivo?</h3>
                <p style='font-size: 1.05em; color: #333;'>Ao acessar o StatsFut, você ganha acesso instantâneo a ferramentas profissionais:</p>
                
                <ul style='list-style-type: none; padding-left: 10px; margin-bottom: 20px;'>
                  <li style='margin-bottom: 10px; color: #333;'>&rsaquo; <strong>Bilhetes Prontos:</strong> Combinações otimizadas matematicamente;</li>
                  <li style='margin-bottom: 10px; color: #333;'>&rsaquo; <strong>Gráficos ao Vivo:</strong> Linhas de gols e cantos atualizadas em tempo real;</li>
                  <li style='margin-bottom: 10px; color: #333;'>&rsaquo; <strong>Alertas de Valor:</strong> Notificações inteligentes enviadas direto no seu celular.</li>
                </ul>
                
                <p style='margin-bottom: 0; text-align: center;'>
                  <a href='https://statsfut.com/' target='_blank' style='background-color: #2e7d32; color: white; padding: 14px 24px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 1.15em; box-shadow: 0 4px 6px rgba(46, 125, 50, 0.3); transition: background-color 0.3s;'>
                    Acessar Painel StatsFut Completo 🚀
                  </a>
                </p>
            </div>
        </div>
        """

        return f"{intro}\n{footer}"
