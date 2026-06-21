import os
import random
import io
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from PIL import Image, ImageDraw, ImageFont

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from matches.models import BetTicket, Match


class Command(BaseCommand):
    help = "Gera análises baseadas nas estatísticas matemáticas do dia e publica no Blogger automaticamente."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Data alvo das dicas no formato AAAA-MM-DD (Padrão: Hoje no fuso de Brasília)."
        )
        parser.add_argument(
            "--test-run",
            action="store_true",
            help="Executa o fluxo de geração e autenticação mas exibe o HTML no terminal em vez de publicar."
        )

    def handle(self, *args, **options):
        # 1. Configurar data alvo (Brasília)
        br_tz = ZoneInfo("America/Sao_Paulo")
        if options["date"]:
            try:
                target_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                self.stderr.write("Formato de data inválido. Use AAAA-MM-DD.")
                return
        else:
            target_date = timezone.now().astimezone(br_tz).date()

        self.stdout.write(f"Iniciando processo para a data: {target_date}...")

        # 2. Buscar bilhetes gerados para a data
        tickets = BetTicket.objects.filter(date_target=target_date).prefetch_related(
            "selections__match__home_team",
            "selections__match__away_team",
            "selections__match__league"
        )

        if not tickets.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Nenhum bilhete encontrado no banco para {target_date}. Certifique-se de que rodou generate_tickets primeiro."
                )
            )
            return

        self.stdout.write(f"Foram encontrados {tickets.count()} bilhetes para processar.")

        # 3. Autenticação na API do Blogger
        self.stdout.write("Conectando à API do Blogger...")
        try:
            blogger_service = self.get_blogger_service()
        except Exception as e:
            self.stderr.write(f"Erro ao autenticar com o Blogger: {e}")
            return

        # 4. Encontrar destaque da rodada primeiro para usar no título
        all_selections = []
        for ticket in tickets:
            for sel in ticket.selections.all():
                if not any(s.match.id == sel.match.id and s.prediction_market == sel.prediction_market for s in all_selections):
                    all_selections.append(sel)

        featured_match = None
        top_sel = None
        if all_selections:
            all_selections.sort(key=lambda s: s.probability, reverse=True)
            top_sel = all_selections[0]
            featured_match = top_sel.match

        # Gerar o Conteúdo HTML e Título
        title = self.generate_title(target_date, featured_match)
        html_content = self.generate_html_content(tickets, target_date, featured_match, all_selections, top_sel)

        # 5. Enviar ou Exibir em Modo Teste
        if options["test_run"]:
            self.stdout.write(self.style.SUCCESS("\n=== MODO TESTE ATIVO ==="))
            self.stdout.write(f"Título do Post: {title}")
            self.stdout.write("Conteúdo HTML Gerado:")
            self.stdout.write("-" * 50)
            self.stdout.write(html_content)
            self.stdout.write("-" * 50)
            self.stdout.write(self.style.SUCCESS("=== FIM DO MODO TESTE (NADA FOI PUBLICADO) ==="))
        else:
            self.stdout.write("Publicando post no Blogger...")
            blog_id = "1194766281316237077"
            
            body = {
                "kind": "blogger#post",
                "blog": {"id": blog_id},
                "title": title,
                "content": html_content,
                # Pode adicionar labels/tags se quiser segmentar os posts
                "labels": ["Palpites de Futebol", "Estatísticas", "Bilhete Pronto"]
            }

            try:
                post = blogger_service.posts().insert(blogId=blog_id, body=body).execute()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Post criado com sucesso! URL: {post.get('url')}"
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
                # run_local_server abre o navegador na máquina onde o comando é executado
                creds = flow.run_local_server(port=0)
            
            # Salvar credenciais no token.json
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())

        return build("blogger", "v3", credentials=creds)

    def generate_banner_image(self, date_str, featured_match=None):
        """Gera uma imagem de capa espetacular usando IA (Pollinations) e adiciona overlay de texto premium."""
        width, height = 800, 450 # Proporção 16:9 que se encaixa melhor em feeds

        # 1. Download de Fontes Premium do Google Fonts (se não existirem)
        font_dir = os.path.join(os.path.dirname(__file__), "fonts")
        os.makedirs(font_dir, exist_ok=True)
        
        font_bold_path = os.path.join(font_dir, "Oswald-Bold.ttf")
        font_regular_path = os.path.join(font_dir, "Montserrat-Regular.ttf")
        font_medium_path = os.path.join(font_dir, "Montserrat-SemiBold.ttf")
        
        def download_font(url, dest_path):
            if not os.path.exists(dest_path):
                try:
                    response = requests.get(url, timeout=15)
                    if response.status_code == 200:
                        with open(dest_path, "wb") as f:
                            f.write(response.content)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Erro ao baixar fonte {os.path.basename(dest_path)}: {e}"))
        
        download_font("https://github.com/google/fonts/raw/main/ofl/oswald/static/Oswald-Bold.ttf", font_bold_path)
        download_font("https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Regular.ttf", font_regular_path)
        download_font("https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-SemiBold.ttf", font_medium_path)

        # 2. Tentar carregar imagem local curada primeiro
        img = None
        curated_dir = os.path.join(settings.BASE_DIR, "curated_images")
        if os.path.exists(curated_dir):
            valid_exts = (".png", ".jpg", ".jpeg", ".webp")
            curated_files = [f for f in os.listdir(curated_dir) if f.lower().endswith(valid_exts)]
            if curated_files:
                selected_file = random.choice(curated_files)
                try:
                    img_path = os.path.join(curated_dir, selected_file)
                    img = Image.open(img_path).convert("RGBA")
                    self.stdout.write(self.style.SUCCESS(f"Usando imagem curada local: {selected_file}"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Erro ao carregar imagem curada {selected_file}: {e}"))

        if not img:
            # 3. Criar Prompt Variado da IA de Futebol com jerseys de cores dinâmicas e seed única
            atmospheres = [
                "at night under bright stadium floodlights",
                "during a golden sunset in a massive crowded stadium",
                "in a futuristic arena with neon light details",
                "in the heavy rain with water splashes on the pitch",
                "with dramatic cinematic smoke and golden light beams"
            ]
            actions = [
                "striking a ball in mid-air",
                "dribbling past a defender in high speed",
                "goalkeeper diving to save a shot near the post",
                "celebrating a goal on the pitch with fans in background",
                "sliding tackle on green grass close-up"
            ]
            styles = [
                "highly detailed sports photography, 8k resolution, cinematic lighting, motion blur",
                "dramatic sports action shot, dynamic angle, award-winning photography, rich colors"
            ]

            selected_atmosphere = random.choice(atmospheres)
            selected_action = random.choice(actions)
            selected_style = random.choice(styles)
            
            colors = ["red", "blue", "white", "black", "yellow", "green", "orange", "purple", "cyan", "magenta"]
            c1 = random.choice(colors)
            colors.remove(c1)
            c2 = random.choice(colors)

            prompt = f"a professional soccer match action shot, player in {c1} jersey vs player in {c2} jersey, {selected_action}, {selected_atmosphere}, {selected_style}"
            
            # Tentar baixar a imagem gerada por IA com seed única para evitar duplicatas
            seed = random.randint(1, 999999)
            try:
                from urllib.parse import quote
                prompt_quoted = quote(prompt)
                ia_url = f"https://image.pollinations.ai/prompt/{prompt_quoted}?width={width}&height={height}&nologo=true&seed={seed}"
                response = requests.get(ia_url, timeout=25)
                if response.status_code == 200:
                    img = Image.open(io.BytesIO(response.content)).convert("RGBA")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Erro ao gerar imagem por IA: {e}"))

        # Fallback caso a IA falhe (IP bloqueado no proxy/VPS ou indisponível)
        if not img:
            # Lista curada de 10 imagens premium de futebol no Unsplash (todas validadas de futebol e retornando 200)
            unsplash_ids = [
                "photo-1529900748604-07564a03e7a6",  # Estádio cheio de torcedores e campo verde
                "photo-1552667466-07770ae110d0",  # Bola clássica no campo de futebol
                "photo-1543351611-58f69d7c1781",  # Refletores de estádio acesos à noite
                "photo-1510566337590-2fc1f21d0faa",  # Trave de gol com bola na rede
                "photo-1551958219-acbc608c6377",  # Bola de futebol no campo sob luz solar
                "photo-1560272564-c83b66b1ad12",  # Jogador de futebol controlando/chutando a bola
                "photo-1606925797300-0b35e9d1794e",  # Trave de futebol e gramado
                "photo-1575361204480-aadea25e6e68",  # Visão ampla do campo de futebol
                "photo-1524015368236-bbf6f72545b6",  # Ação de jogo / bola sob o pé de jogador
                "photo-1518604666860-9ed391f76460"   # Refletores do estádio ao fundo
            ]
            selected_id = random.choice(unsplash_ids)
            fallback_url = f"https://images.unsplash.com/{selected_id}?auto=format&fit=crop&w={width}&h={height}&q=80"
            try:
                response = requests.get(fallback_url, timeout=15)
                if response.status_code == 200:
                    img = Image.open(io.BytesIO(response.content)).convert("RGBA")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Erro ao baixar imagem de fallback do Unsplash: {e}"))
                
        if not img:
            # Fallback final se até o Unsplash falhar
            img = Image.new("RGBA", (width, height), color="#0c2d15")
            draw = ImageDraw.Draw(img)
            for i in range(0, width + height, 20):
                draw.line([i, 0, i - height, height], fill="#113f18", width=3)
        else:
            img = img.resize((width, height))

        # 4. Adicionar Overlay de Texto Premium
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Desenhar uma placa elegante (Card premium central/inferior com glassmorphism translúcido)
        # Coordenadas do box: margens de 30px nas laterais, base a 20px da borda inferior
        card_x1, card_y1 = 40, height - 150
        card_x2, card_y2 = width - 40, height - 20
        
        # Preenchimento escuro premium semi-transparente (Sleek Charcoal/Slate)
        overlay_draw.rounded_rectangle(
            [card_x1, card_y1, card_x2, card_y2], 
            radius=15, 
            fill=(10, 15, 30, 220),  # Azul muito escuro / quase preto translúcido
            outline=(255, 179, 0, 160),  # Borda dourada semi-transparente
            width=2
        )

        img = Image.alpha_composite(img, overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Carregador de fontes do sistema/projeto
        def get_font(font_path, size):
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    pass
            return ImageFont.load_default()

        font_title = get_font(font_bold_path, 28)     # Oswald-Bold para o confronto
        font_sub = get_font(font_medium_path, 15)      # Montserrat-SemiBold para a liga
        font_desc = get_font(font_regular_path, 13)    # Montserrat-Regular para rodada
        font_brand = get_font(font_bold_path, 11)      # Oswald para badge
        font_watermark = get_font(font_medium_path, 12) # Montserrat para a URL

        # Limpar acentuações para evitar glifos inválidos (retângulos vazios)
        def clean_txt(text):
            import unicodedata
            normalized = unicodedata.normalize('NFD', str(text))
            # Remove acentos e caracteres não suportados como • (troca por |)
            cleaned = "".join(c for c in normalized if unicodedata.category(c) != 'Mn')
            return cleaned.replace("•", "|").replace("º", "").strip()

        # Desenhar textos e badge
        if featured_match:
            text_badge = f"DESTAQUE DO DIA | {featured_match.league.name.upper()}"
            text_match = f"{featured_match.home_team.name.upper()}  VS  {featured_match.away_team.name.upper()}"
            text_date = f"Estatisticas e Palpites de Futebol | Rodada de {date_str}"
        else:
            text_badge = "PALPITE DE HOJE"
            text_match = "ESTATISTICAS E BILHETES PRONTOS"
            text_date = f"Dicas e Palpites de Valor para {date_str}"

        # Aplicar limpeza de caracteres
        text_badge = clean_txt(text_badge)
        text_match = clean_txt(text_match)
        text_date = clean_txt(text_date)

        # 1. Badge "DESTAQUE" com fundo dourado
        badge_w = draw.textlength(text_badge, font=font_brand) + 20
        badge_h = 24
        badge_x1 = (width - badge_w) // 2
        badge_y1 = card_y1 + 15
        badge_x2 = badge_x1 + badge_w
        badge_y2 = badge_y1 + badge_h
        
        # Desenhar fundo do badge
        draw.rounded_rectangle([badge_x1, badge_y1, badge_x2, badge_y2], radius=6, fill="#ffb300")
        # Texto do badge
        draw.text(((badge_x1 + badge_x2) // 2, (badge_y1 + badge_y2) // 2), text_badge, fill="#0a0f1e", font=font_brand, anchor="mm")

        # 2. Confronto (Título principal)
        draw.text((width // 2, card_y1 + 68), text_match, fill="#ffffff", font=font_title, anchor="mm")

        # 3. Linha divisória sutil
        line_y = card_y1 + 95
        draw.line([(width // 2) - 150, line_y, (width // 2) + 150, line_y], fill=(255, 179, 0, 100), width=1)

        # 4. Descrição / Data
        draw.text((width // 2, card_y1 + 115), text_date, fill="#4edf93", font=font_desc, anchor="mm")

        # 5. Watermark de marca com fundo semi-transparente no canto superior direito
        watermark_text = "statsfut.com"
        wm_w = draw.textlength(watermark_text, font=font_watermark) + 16
        wm_h = 28
        wm_x1 = width - wm_w - 20
        wm_y1 = 20
        
        # Desenhar badge da watermark
        draw.rounded_rectangle([wm_x1, wm_y1, wm_x1 + wm_w, wm_y1 + wm_h], radius=6, fill=(10, 15, 30, 180))
        draw.text((wm_x1 + (wm_w // 2), wm_y1 + (wm_h // 2)), watermark_text, fill="#ffffff", font=font_watermark, anchor="mm")

        # Salvar em buffer de memória
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        return img_byte_arr.getvalue()

    def upload_to_catbox(self, image_bytes, filename="banner.png", mime_type="image/png"):
        """Envia os bytes da imagem para o Catbox e retorna o link direto."""
        url = "https://catbox.moe/user/api.php"
        data = {"reqtype": "fileupload"}
        files = {"fileToUpload": (filename, image_bytes, mime_type)}
        try:
            response = requests.post(url, data=data, files=files, timeout=15)
            if response.status_code == 200:
                return response.text.strip()
            else:
                self.stdout.write(self.style.WARNING(f"Erro no Catbox. Status: {response.status_code}, Resposta: {response.text}"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Erro ao subir imagem para o Catbox: {e}"))
        return None

    def generate_title(self, target_date, featured_match=None):
        """Gera títulos humanos, atraentes e dinâmicos para SEO sem parecer robótico."""
        date_str = target_date.strftime("%d/%m/%Y")
        
        # Se tivermos um jogo de destaque, colocamos no título para chamar a atenção
        if featured_match:
            home = featured_match.home_team.name
            away = featured_match.away_team.name
            templates = [
                f"Palpites de Hoje: {home} x {away} e as melhores dicas de futebol ({date_str})",
                f"Onde apostar hoje? {home} x {away} e principais palpites ({date_str})",
                f"Analise de {home} x {away} e dicas quentes para apostar hoje ({date_str})",
                f"Dicas de futebol {date_str}: Foco em {home} x {away} e bilhete pronto",
                f"Palpites de futebol para hoje: {home} x {away} e dicas do dia ({date_str})"
            ]
        else:
            templates = [
                f"Palpites de hoje: Nossas dicas quentes de futebol para {date_str}",
                f"Onde estao os melhores jogos para apostar hoje? ({date_str})",
                f"Jogos de hoje: Dicas e analise para lucrar nesta rodada ({date_str})",
                f"Dicas de apostas para {date_str}: Melhores jogos e bilhete pronto",
                f"Bilhete Pronto e Palpites de Futebol para hoje ({date_str})"
            ]
        return random.choice(templates)

    def generate_html_content(self, tickets, target_date, featured_match=None, all_selections=None, top_sel=None):
        """Cria o corpo do post em formato HTML estruturado."""
        date_str = target_date.strftime("%d/%m/%Y")
        
        # 1. Introdução Variada (Conversacional e Humana)
        intro_templates = [
            f"<p>Fala galera! Trazemos hoje a analise completa e palpites do <strong>StatsFut</strong> para os jogos do dia <strong>{date_str}</strong>. Filtramos a nossa base de dados de dezenas de ligas pelo mundo para destacar os confrontos com melhor tendencia.</p>",
            f"<p>Preparados para a rodada de hoje (<strong>{date_str}</strong>)? O nosso sistema analisou os numeros das principais ligas para destacar algumas dicas de valor gratuitas. Confira abaixo as melhores oportunidades que separamos para hoje!</p>",
            f"<p>Quer dar uma olhada nas estatisticas dos jogos de hoje, dia <strong>{date_str}</strong>? Preparamos alguns prognosticos individuais baseados em consistencia e comportamento recente dos times. Veja onde estao as melhores chances!</p>"
        ]
        html = random.choice(intro_templates)

        # Usar imagem curada da pasta curated_images (sem edição, sem overlay)
        image_url = None
        curated_dir = os.path.join(settings.BASE_DIR, "curated_images")
        if os.path.exists(curated_dir):
            valid_exts = (".png", ".jpg", ".jpeg", ".webp")
            curated_files = [f for f in os.listdir(curated_dir) if f.lower().endswith(valid_exts)]
            if curated_files:
                selected_file = random.choice(curated_files)
                img_path = os.path.join(curated_dir, selected_file)
                self.stdout.write(self.style.SUCCESS(f"Usando imagem curada local: {selected_file}"))
                try:
                    with open(img_path, "rb") as f:
                        image_bytes = f.read()
                    
                    # Determinar mime_type
                    ext = selected_file.lower().split('.')[-1]
                    mime_type = "image/jpeg"
                    if ext == "png":
                        mime_type = "image/png"
                    elif ext == "webp":
                        mime_type = "image/webp"

                    image_url = self.upload_to_catbox(image_bytes, filename=selected_file, mime_type=mime_type)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Erro ao ler/enviar imagem curada {selected_file}: {e}"))

        if not image_url:
            # Fallback caso não tenha imagens curadas ou dê erro no upload
            self.stdout.write(self.style.WARNING(f"Aviso: Usando imagem de fallback. O link do catbox não foi retornado."))
            image_url = "https://images.unsplash.com/photo-1529900748604-07564a03e7a6?auto=format&fit=crop&w=800&q=80"

        html += f'<p><img src="{image_url}" alt="Palpites de Futebol e Estatísticas" style="width: 100%; max-width: 600px; height: auto; border-radius: 8px; margin: 15px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" /></p>'

        if featured_match and top_sel:
            # Tenta encontrar estatísticas interessantes das equipes para contextualizar
            home_over25 = featured_match.home_team.get_stats("over25")
            away_over25 = featured_match.away_team.get_stats("over25")
            
            html += "<hr/>"
            html += f"<h2>⭐ Destaque Estatístico da Rodada: {featured_match.home_team.name} vs {featured_match.away_team.name}</h2>"
            html += f"<p>Nosso modelo quantitativo identificou que o jogo mais consistente para hoje é o confronto entre <strong>{featured_match.home_team.name}</strong> e <strong>{featured_match.away_team.name}</strong>, válido pela liga <em>{featured_match.league.name} ({featured_match.league.country})</em>.</p>"
            
            # Texto contextualizado dependendo do mercado
            market_lower = top_sel.prediction_market.lower()
            if "over" in market_lower or "goals" in market_lower:
                html += f"<p>A indicação sugerida é <strong>{top_sel.prediction_label}</strong>, com uma confiança calculada de <strong>{top_sel.probability}%</strong>. "
                html += f"Historicamente, o {featured_match.home_team.name} possui uma média de over de <strong>{home_over25}%</strong> nas últimas partidas em casa, enquanto o {featured_match.away_team.name} atinge <strong>{away_over25}%</strong> de jogos movimentados em partidas recentes fora de seus domínios.</p>"
            else:
                html += f"<p>A estatística sugere o mercado de <strong>{top_sel.prediction_label}</strong> (Confiança: <strong>{top_sel.probability}%</strong>). Ambas as equipes vêm se mostrando muito fiéis às linhas estatísticas traçadas pelo sistema.</p>"

        # 3. Listar 3 Dicas Individuais Gratuitas do Dia (Funil de Vendas)
        html += "<hr/>"
        html += "<h2>📋 Principais Dicas Gratuitas de Hoje</h2>"
        html += "<p>Confira 3 palpites selecionados pelo nosso algoritmo estatístico para a rodada de hoje:</p>"

        # Pega as 3 melhores dicas individuais (excluindo o destaque se possível, ou simplesmente as 3 primeiras)
        tips_to_show = all_selections[:3]
        for sel in tips_to_show:
            m = sel.match
            html += f"<div style='border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 15px; background-color: #fafafa;'>"
            html += f"<h3 style='margin-top:0; color: #2e7d32;'>⚽ {m.home_team.name} vs {m.away_team.name}</h3>"
            html += f"<p style='margin: 5px 0;'><strong>Liga:</strong> {m.league.name} ({m.league.country})</p>"
            html += f"<p style='margin: 5px 0;'><strong>Palpite sugerido:</strong> <strong>{sel.prediction_label}</strong> (Confidence: {sel.probability}%)</p>"
            html += f"<p style='margin: 5px 0; font-size: 0.9em; color: #555;'>Média de odd aproximada: <em>@{sel.odd}</em></p>"
            html += "</div>"

        # 4. Box de Restrição do Premium (Gatilho mental para acessar o site)
        html += "<div style='background-color: #fff8e1; border-left: 6px solid #ffb300; padding: 15px; margin: 25px 0; border-radius: 4px;'>"
        html += "<h4 style='margin-top: 0; color: #b78103; font-size: 1.1em;'>🔐 Bilhetes Prontos e Trixies Bloqueados</h4>"
        html += f"<p style='margin: 0; font-size: 0.95em; color: #555;'>Os bilhetes combinados estruturados de hoje (incluindo as <strong>Duplas de Gols</strong>, <strong>Triplas de Cantos</strong>, <strong>Sistemas Trixie</strong> e as <strong>Múltiplas de Ouro</strong> de odds gigantes) são exclusivos do nosso plano premium no painel. O robô gerou diversos bilhetes para este dia {date_str} que estão disponíveis somente no site oficial.</p>"
        html += "</div>"

        # 5. Rodapé e CTA (Call to Action) para trazer tráfego para o site Python
        html += "<hr/>"
        html += "<div style='background-color: #e8f5e9; padding: 20px; border-left: 6px solid #2e7d32; border-radius: 4px; margin-top: 20px;'>"
        html += "<h3 style='margin-top:0; color: #1b5e20;'>📊 Quer ver todos os bilhetes prontos e estatísticas ao vivo?</h3>"
        html += "<p>As análises apresentadas acima são apenas um pequeno teaser. Ao acessar o StatsFut, você ganha acesso instantâneo a:</p>"
        html += "<ul>"
        html += "<li><strong>Bilhetes Prontos:</strong> Combinações otimizadas para maximizar o ganho;</li>"
        html += "<li><strong>Gráficos ao Vivo:</strong> Linhas de gols e cantos (escanteios) em tempo real;</li>"
        html += "<li><strong>Alertas de Valor:</strong> Notificações inteligentes enviadas direto no seu painel;</li>"
        html += "<li><strong>Estatísticas Avançadas:</strong> Banco de dados de mais de 50 ligas atualizados via Tor.</li>"
        html += "</ul>"
        html += "<p style='margin-bottom: 0; margin-top: 15px;'>"
        html += f"<a href='https://statsfut.com' style='background-color: #2e7d32; color: white; padding: 12px 20px; text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 1.1em;'>Acessar Painel StatsFut Completo 🚀</a>"
        html += "</p>"
        html += "</div>"

        return html
