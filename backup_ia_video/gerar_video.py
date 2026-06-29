import os
import sys
import time
import json
import urllib.request
import urllib.error
import argparse
import requests
from playwright.sync_api import sync_playwright
from moviepy import VideoFileClip, AudioFileClip

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    print("=" * 60)
    print("      STATSFUT - GERADOR DE VÍDEOS DINÂMICOS COM SINCRONIZAÇÃO IA    ")
    print("=" * 60)
    print("Este script grava a tela do navegador executando uma coreografia")
    print("sincronizada de forma INTELIGENTE pela IA baseada no seu roteiro!")
    print("A tela branca inicial de carregamento será cortada automaticamente.")
    print("=" * 60)

def load_deepseek_api_key():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("DEEPSEEK_API_KEY="):
                    return line.strip().split("DEEPSEEK_API_KEY=")[1].strip()
    return os.environ.get("DEEPSEEK_API_KEY")

def analyze_script_timeline(api_key, roteiro_text, audio_duration, audio_path):
    import re
    import os
    import math
    import imageio_ffmpeg
    
    # Injetar o FFmpeg que já vem com o MoviePy no PATH do Windows para o Whisper usá-lo
    ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
    os.environ["PATH"] += os.pathsep + ffmpeg_dir
    
    import whisper

    print("\n[MÁQUINA] Iniciando escuta com Inteligência Artificial (OpenAI Whisper)...")
    
    # 1. Carrega o modelo de IA no disco E: para poupar o disco C:
    model_dir = "E:\\WHISPER_MODELS"
    os.makedirs(model_dir, exist_ok=True)
    
    # O modelo "tiny" (aprox 75MB) é extremamente rápido e suficiente para alinhamento forçado
    print(f"  - Carregando cérebro Whisper (Modelo: tiny) a partir de: {model_dir}")
    model = whisper.load_model("tiny", download_root=model_dir)
    
    # O librosa falha miseravelmente ao medir a duração de MP3 em formato VBR (ex: gerado pelo gTTS)
    # Vamos usar o próprio moviepy que já é importado embaixo para ter a duração matemática real do arquivo
    from moviepy import AudioFileClip
    temp_audio_clip = AudioFileClip(audio_path)
    audio_duration = temp_audio_clip.duration
    temp_audio_clip.close()
    
    print(f"  - Ouvindo o arquivo de áudio para capturar milissegundos exatos: {audio_path}")
    # Transcreve ativando os carimbos de tempo em nível de palavra
    result = model.transcribe(audio_path, word_timestamps=True, language="pt")
    
    print("\n[MÁQUINA] Cruzando os tempos do áudio com as tags do roteiro via Busca Direta de Foco...")
    
    # 1. Isolar apenas a parte do roteiro da máquina
    machine_idx = roteiro_text.find("TEXTO DA MÁQUINA (COPIE TUDO AQUI ABAIXO")
    if machine_idx != -1:
        roteiro_text = roteiro_text[machine_idx:]
    else:
        machine_idx = roteiro_text.find("ROTEIRO DA MÁQUINA")
        if machine_idx != -1:
            roteiro_text = roteiro_text[machine_idx:]
            
    roteiro_text = re.sub(r'👇.*?👇', '', roteiro_text)
    roteiro_text = roteiro_text.replace("TEXTO DA MÁQUINA (COPIE TUDO AQUI ABAIXO E COLE NO ARQUIVO roteiro.txt)", "")
    
    # 2. Extrair o texto falado do Whisper com carimbos de tempo por caractere
    audio_words = []
    for segment in result['segments']:
        for word in segment.get('words', []):
            clean = re.sub(r'[^\w\s]', '', word['word'].lower().strip())
            if clean:
                audio_words.append({
                    "text": clean,
                    "start": word['start'],
                    "end": word['end']
                })

    # Total duration of audio
    audio_duration = result['segments'][-1]['words'][-1]['end'] if result.get('segments') else audio_duration
    
    # 3. Limpar o roteiro e mapear onde as tags ocorrem
    tags = []
    for match in re.finditer(r'\[(.*?)\]', roteiro_text):
        tag_content = match.group(1).strip()
        tag_start = match.start()
        tag_end = match.end()
        
        is_off = (tag_content.upper() == 'OFF')
        foco_text = ""
        anchor_words = []
        full_words_after = []
        
        if tag_content.upper().startswith('FOCO:'):
            foco_text = tag_content[5:].strip()
            # Pega as palavras imediatamente APÓS a tag no roteiro
            text_after = roteiro_text[tag_end:]
            full_words_after = text_after.split()[:25] # Pega até 25 palavras originais (com as pequenas) para cálculo de offset massivo
            words_after = [w for w in re.sub(r'[^\w\s]', '', text_after.lower()).split() if len(w) > 1]
            if words_after:
                anchor_words = words_after[:12] # Guarda até 12 âncoras para segurança extrema!
                
        tags.append({
            "content": tag_content,
            "is_off": is_off,
            "foco_text": foco_text,
            "anchor_words": anchor_words,
            "full_words_after": full_words_after,
            "char_idx": tag_start
        })

    events = []
    current_tab = "gols"
    
    events.append({
        "time": 0.0,
        "selector": "", 
        "tab": "gols",
        "description": "Início da análise",
        "has_text": ""
    })

    search_start_idx = 0
    
    for i, t in enumerate(tags):
        tag_content = t["content"]
        is_off = t["is_off"]
        foco_text = t["foco_text"]
        anchor_words = t["anchor_words"]
        full_words_after = t["full_words_after"]
        
        if tag_content.upper().startswith('ABA:'):
            current_tab = tag_content[4:].strip().lower()
            continue
            
        if is_off:
            continue
            
        if foco_text:
            best_idx = -1
            matched_word = ""
            
            # Estima o ponto do áudio baseado na posição do caractere no texto
            estimated_idx = int((t["char_idx"] / len(roteiro_text)) * len(audio_words))
            
            # Procura num raio de 60 palavras para trás e 60 palavras para frente
            window_start = max(search_start_idx, estimated_idx - 60)
            window_end = min(len(audio_words), estimated_idx + 60)
            
            if anchor_words:
                for aw in anchor_words:
                    for j in range(window_start, window_end):
                        w = audio_words[j]['text']
                        if aw == w or (len(aw) > 3 and aw in w):
                            best_idx = j
                            matched_word = aw
                            break
                    if best_idx != -1:
                        break # Achou uma das âncoras válidas!
                        
            if best_idx != -1:
                # Recuperar o offset real da palavra ancorada
                clean_full_words = [re.sub(r'[^\w\s]', '', w.lower()) for w in full_words_after]
                aw_offset = 0
                for k, cw in enumerate(clean_full_words):
                    if not cw: continue
                    if cw == matched_word or (len(matched_word) > 3 and matched_word in cw):
                        aw_offset = k
                        break
                        
                # Subtrai o offset para voltar ao início da frase
                start_idx = max(search_start_idx, best_idx - aw_offset)
                event_time = audio_words[start_idx]['start']
                search_start_idx = best_idx + 1
            else:
                event_time = (t["char_idx"] / len(roteiro_text)) * audio_duration
                
            events.append({
                "tag_idx": i,
                "is_off": False,
                "time": round(event_time, 2),
                "selector": "", 
                "tab": current_tab,
                "description": foco_text,
                "has_text": foco_text
            })

    # 4. Inserir os OFFs perfeitamente cronometrados ANTES do próximo Foco
    final_events = []
    final_events.append(events[0])
    
    for i in range(1, len(events)):
        prev_event = events[i-1]
        curr_event = events[i]
        
        # Ignora o Início da análise para não botar OFF nele
        if i > 1:
            # Apaga o destaque 0.5 segundos antes do próximo foco iniciar, criando um pulo perfeito
            off_time = curr_event["time"] - 0.5
            if off_time <= prev_event["time"]:
                off_time = curr_event["time"] - 0.1
                
            final_events.append({
                "time": round(off_time, 2),
                "selector": "", 
                "tab": prev_event["tab"],
                "description": "Limpar Destaque",
                "has_text": "CLEAR_HIGHLIGHTS"
            })
            
        final_events.append(curr_event)

    # Último OFF da tela
    if len(final_events) > 1:
        final_events.append({
            "time": round(audio_duration - 0.5, 2),
            "selector": "", 
            "tab": final_events[-1]["tab"],
            "description": "Limpar Destaque",
            "has_text": "CLEAR_HIGHLIGHTS"
        })
        
    events = final_events

    
    # Remove redundâncias de início
    if len(events) > 1 and events[1]["time"] < 1.0:
        events.pop(0)

    print(f"  [SUCESSO] Cronograma matemático gerado com {len(events)} eventos focais.")
    for e in events:
        print(f"    - {e['time']}s: Aba [{e['tab']}] -> Foco: '{e['description']}'")
        
    return events

def run_choreography(page, total_duration, timeline=None):
    print("\n[2/4] Iniciando coreografia de gravação de tela de cinema...")
    
    # Injetar CSS de destaque premium na página e funções JS de rolagem linear suave/troca de abas
    page.evaluate("""
        const style = document.createElement('style');
        style.innerHTML = `
            @keyframes sf-pulse-border {
                0%, 100% { box-shadow: 0 0 8px rgba(249, 115, 22, 0.3); }
                50% { box-shadow: 0 0 25px rgba(249, 115, 22, 0.9), 0 0 50px rgba(249, 115, 22, 0.4); }
            }
            .sf-highlight {
                animation: sf-pulse-border 1.5s ease-in-out infinite !important;
                border: 3px solid #f97316 !important;
                border-radius: 10px !important;
                z-index: 9999 !important;
                position: relative !important;
            }
            .sf-highlight::after {
                content: '' !important;
                position: absolute !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                bottom: 0 !important;
                background: rgba(249, 115, 22, 0.25) !important;
                border-radius: 8px !important;
                pointer-events: none !important;
                z-index: 9999 !important;
            }
        `;
        document.head.appendChild(style);

        // Rolagem de cinema linear e suave com Promise
        window.sf_smooth_scroll_to = function(targetY, durationMs) {
            return new Promise((resolve) => {
                const startY = window.scrollY;
                const difference = targetY - startY;
                const startTime = performance.now();

                function step() {
                    const now = performance.now();
                    const elapsed = now - startTime;
                    const progress = Math.min(elapsed / durationMs, 1);
                    
                    // Ease in-out quadratic formula
                    const ease = progress < 0.5 
                        ? 2 * progress * progress 
                        : -1 + (4 - 2 * progress) * progress;

                    window.scrollTo(0, startY + difference * ease);

                    if (progress < 1) {
                        window.requestAnimationFrame(step);
                    } else {
                        resolve();
                    }
                }
                window.requestAnimationFrame(step);
            });
        };

        // Troca de abas multilíngue ultra-robusta com fallback de manipulação direta de classes no DOM
        window.sf_switch_tab = function(tabName) {
            try {
                // 1. Tentar chamar a função JS nativa
                if (typeof switchMarketTab === 'function') {
                    try {
                        switchMarketTab(tabName);
                        return true;
                    } catch (innerErr) {
                        console.warn("Erro ao chamar switchMarketTab nativo:", innerErr);
                    }
                }

                // 2. Tentar clique direto por onclick contendo o nome do mercado
                let btn = document.querySelector(`button[onclick*='${tabName}']`);
                if (btn) {
                    try {
                        btn.click();
                        return true;
                    } catch (clickErr) {
                        console.warn("Erro ao clicar no botão:", clickErr);
                    }
                }

                // 3. Fallback absoluto: Forçar manipulação de classes no DOM diretamente
                console.log("Forçando troca de abas via manipulação direta de DOM para:", tabName);
                
                // Mapear tabNames em português e inglês para robustez
                const possibleNames = [tabName];
                if (tabName === 'escanteios') possibleNames.push('corners', 'cantos');
                if (tabName === 'especiais') possibleNames.push('specials', 'combos');
                if (tabName === 'cartoes') possibleNames.push('cards', 'cartões');
                if (tabName === 'gols') possibleNames.push('goals', 'halves');
                if (tabName === 'chutes') possibleNames.push('shots');
                if (tabName === 'lays') possibleNames.push('trade', 'lays');

                let matchedBtn = null;
                document.querySelectorAll('.market-tab-btn, button').forEach(b => {
                    const txt = b.textContent.toLowerCase();
                    const clickAttr = b.getAttribute('onclick') || '';
                    
                    const matches = possibleNames.some(name => clickAttr.includes(name) || txt.includes(name));
                    if (matches) {
                        matchedBtn = b;
                    }
                });

                if (matchedBtn) {
                    console.log("Forçando clique na aba:", matchedBtn.textContent);
                    matchedBtn.click();
                    return true;
                }

                return false;
            } catch (e) {
                console.error("Erro geral ao trocar aba:", e);
            }
            return false;
        };

        // Foca em um elemento específico com rolagem e destaque
        window.sf_focus_element = async function(selector, tabName, hasText) {
            // 1. Limpa destaques anteriores com transição suave
            document.querySelectorAll('.sf-highlight').forEach(el => {
                el.classList.remove('sf-highlight');
                el.style.transition = 'all 0.5s ease';
            });
            
            // 2. Troca de aba se necessário
            if (tabName) {
                // Sobe suavemente até o menu de abas para o espectador ver o clique acontecendo!
                const tabMenu = document.querySelector('.market-tabs, .market-tab-btn');
                if (tabMenu) {
                    const rect = tabMenu.getBoundingClientRect();
                    const targetY = window.scrollY + rect.top - 120;
                    await window.sf_smooth_scroll_to(Math.max(0, targetY), 1200);
                }
                
                window.sf_switch_tab(tabName);
                await new Promise(r => setTimeout(r, 1200)); // Aguarda carregamento
            }
            
            // 3. Busca em 2 passes: primeiro texto exato, depois números com word-boundary
            let el = null;
            if (hasText && hasText.trim() !== "") {
                const targetText = hasText.toLowerCase().replace(/\\s+/g, ' ').trim();
                const specificWidgets = document.querySelectorAll('.hbar-row, .mini-widget, .combo-pill, .lay-row, .tug-row, .grid-elite-2 > div, .mg-row');
                
                // PASSE 1: Texto exato (mais confiável - ex: "47%" só bate onde tem "47%" literal)
                for (let e of specificWidgets) {
                    if (!e.textContent) continue;
                    const eText = e.textContent.toLowerCase().replace(/\\s+/g, ' ').trim();
                    if (eText.includes(targetText)) {
                        el = e;
                        break;
                    }
                }
                
                // PASSE 2: Números com word-boundary (evita que "47" bata em "1.47")
                if (!el) {
                    const numbers = targetText.match(/\\d+(\\.\\d+)?/g);
                    if (numbers && numbers.length > 0) {
                        for (let e of specificWidgets) {
                            if (!e.textContent) continue;
                            const eText = e.textContent.toLowerCase().replace(/\\s+/g, ' ').trim();
                            let allFound = true;
                            for (let num of numbers) {
                                // Word-boundary: o número não pode estar grudado em outro dígito ou ponto
                                const regex = new RegExp('(?<![0-9.])' + num.replace('.', '\\\\.') + '(?![0-9])', 'g');
                                if (!regex.test(eText)) { allFound = false; break; }
                            }
                            if (allFound) { el = e; break; }
                        }
                    }
                }
            }
            
            // 4. Fallback para CSS purista se o texto falhar
            if (!el && selector) {
                let cleanSelector = selector;
                if (selector.startsWith('#tab-')) {
                    const parts = selector.split(' ');
                    if (parts.length > 1) {
                        cleanSelector = parts.slice(1).join(' ');
                    }
                }
                el = document.querySelector(cleanSelector) || document.querySelector(selector);
            }

            // 5. Destaca e rola até o elemento
            if (el) {
                el.classList.add('sf-highlight');
                const rect = el.getBoundingClientRect();
                const targetY = window.scrollY + rect.top - (window.innerHeight - rect.height) / 2;
                await window.sf_smooth_scroll_to(Math.max(0, targetY), 1500); // 1.5s rolagem suave
                return true;
            } else {
                // Fallback: se o elemento não for achado, rola até o painel ativo correspondente
                const activeTab = document.querySelector('.market-tab-content.active');
                if (activeTab) {
                    const rect = activeTab.getBoundingClientRect();
                    const targetY = window.scrollY + rect.top - 80;
                    await window.sf_smooth_scroll_to(Math.max(0, targetY), 1200);
                }
            }
            return false;
        };

        window.sf_clear_highlights = function() {
            document.querySelectorAll('.sf-highlight').forEach(el => el.classList.remove('sf-highlight'));
        };
    """)

    if not timeline:
        print("  - Usando cronograma de sincronização padrão...")
        timeline = [
            {"time": 0.0, "selector": ".premium-dashboard, .match-hero-minimal, .match-hero", "tab": "gols", "description": "Topo da página"},
            {"time": total_duration * 0.10, "selector": ".ring-group", "tab": "gols", "description": "Anéis de Gols"},
            {"time": total_duration * 0.35, "selector": ".btts-pie-box, .result-box", "tab": "gols", "description": "BTTS e HT Goals"},
            {"time": total_duration * 0.55, "selector": ".corner-team-panel", "tab": "escanteios", "description": "Escanteios"},
            {"time": total_duration * 0.70, "selector": ".combo-pill, .stat-card-premium", "tab": "especiais", "description": "Especiais & Combos"},
            {"time": total_duration * 0.85, "selector": ".ia-panel-modern", "tab": "gols", "description": "Resumo da IA"}
        ]

    # Ordenar cronograma pelo tempo
    timeline = sorted(timeline, key=lambda x: x["time"])
    current_tab = "gols"

    start_time = time.time()
    for i, event in enumerate(timeline):
        target_time = event["time"]
        selector = event.get("selector", "")
        tab = event.get("tab", "")
        description = event.get("description", "")
        has_text = event.get("has_text", "")
        
        elapsed = time.time() - start_time
        sleep_needed = target_time - elapsed
        if sleep_needed > 0:
            time.sleep(sleep_needed)
            
        print(f"  -> Evento [{i+1}/{len(timeline)}]: {description} (~{target_time:.1f}s)")
        
        # Executa foco completo ou limpa a tela se for a tag [OFF]
        if has_text == "CLEAR_HIGHLIGHTS":
            page.evaluate("window.sf_clear_highlights()")
        else:
            page.evaluate(f"window.sf_focus_element({json.dumps(selector)}, {json.dumps(tab) if tab != current_tab else 'null'}, {json.dumps(has_text)})")
            
        current_tab = tab
        
    # Aguarda o restante do tempo total
    elapsed = time.time() - start_time
    remaining = total_duration - elapsed
    if remaining > 0:
        time.sleep(remaining)
        
    # Limpa destaques e sobe
    page.evaluate("window.sf_clear_highlights()")
    page.evaluate("window.sf_smooth_scroll_to(0, 2000)")
    time.sleep(2.0)

    actual_duration = time.time() - start_time
    print(f"\n[SUCESSO] Coreografia finalizada em {actual_duration:.2f}s (esperado: {total_duration:.2f}s)")

def capture_video_recording(match_url, temp_dir, duration, timeline=None):
    print("\n[1/4] Iniciando gravação de tela automatizada no Playwright...")
    video_temp_path = None
    loading_duration = 0.0

    with sync_playwright() as p:
        print("  - Lançando navegador (chromium)...")
        browser = p.chromium.launch(headless=True)
        
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=temp_dir,
            record_video_size={"width": 1920, "height": 1080},
            locale="pt-BR"
        )
        
        page = context.new_page()
        
        start_loading = time.time()
        print(f"  - Acessando página da partida: {match_url}")
        try:
            page.goto(match_url, wait_until="networkidle", timeout=60000)
        except Exception:
            print("  [AVISO] Timeout na carga de rede, tentando prosseguir...")

        time.sleep(3) # Aguarda gráficos
        loading_duration = time.time() - start_loading

        # Remover cookies consent banner e modais do Statsfut de forma absoluta para manter o vídeo limpo
        page.evaluate("""
            // Remover banners de consentimento de cookies
            document.querySelectorAll("div, section, p, button, a").forEach(el => {
                const txt = el.textContent.toLowerCase();
                const id = el.id.toLowerCase();
                const cls = el.className.toLowerCase();
                if (txt.includes("cookie") || txt.includes("cookies") || id.includes("cookie") || cls.includes("cookie") || txt.includes("consent")) {
                    if (el.tagName !== 'BODY' && el.tagName !== 'HTML') {
                        el.remove();
                    }
                }
            });
            // Remover modais normais
            document.querySelectorAll('.video-script-modal, .modal-backdrop, .modal').forEach(e => e.remove());
        """)
        time.sleep(1)
        loading_duration += 1.0

        # Inicia a coreografia de cinema
        run_choreography(page, duration, timeline)

        video_temp_path = page.video.path()
        
        context.close()
        browser.close()
        
    return video_temp_path, loading_duration

def merge_video_audio(video_path, audio_path, output_path, loading_duration):
    print("\n[3/4] Mesclando gravação de tela e áudio da narração...")
    
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)
    
    print(f"  - Vídeo gravado (com loading): {video_clip.duration:.2f}s | Áudio original: {audio_clip.duration:.2f}s")
    print(f"  - Cortando {loading_duration:.2f}s iniciais de tela branca...")
    
    # Corta o início em branco
    video_clip = video_clip.subclipped(loading_duration, loading_duration + audio_clip.duration)
    
    final_clip = video_clip.with_audio(audio_clip)
    
    print("\n[4/4] Renderizando arquivo MP4 final para o YouTube...")
    final_clip.write_videofile(
        output_path,
        fps=25,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=8,
        logger="bar"
    )
    
    video_clip.close()
    audio_clip.close()
    final_clip.close()

def main():
    parser = argparse.ArgumentParser(description="Gerador Automático de Vídeos Statsfut")
    parser.add_argument("--url", type=str, help="URL da partida no Statsfut")
    parser.add_argument("--audio", type=str, help="Caminho para o arquivo de áudio (.mp3)")
    parser.add_argument("--roteiro", type=str, help="Caminho para o arquivo de texto com o roteiro")
    
    args = parser.parse_args()

    clear_screen()
    print_banner()

    # URL da partida
    if args.url:
        match_url = args.url
        print(f"URL recebida via CMD: {match_url}")
    else:
        print("Digite ou cole a URL da partida do Statsfut (ex: http://127.0.0.1:8000/match/123/...):")
        match_url = input("> ").strip()

    if not match_url:
        print("[ERRO] A URL é obrigatória!")
        sys.exit(1)

    # Arquivo de áudio da narração
    if args.audio:
        audio_path = args.audio
        print(f"Áudio recebido via CMD: {audio_path}")
    else:
        print("\nArraste e solte o arquivo de áudio (.mp3) ou digite o caminho:")
        audio_path = input("> ").strip().replace('"', '').replace("'", "")

    if not audio_path or not os.path.exists(audio_path):
        print(f"[ERRO] Arquivo de áudio não encontrado no caminho: {audio_path}")
        sys.exit(1)

    # Coleta de roteiro opcional
    roteiro_text = ""
    if args.roteiro:
        print(f"Roteiro recebido via CMD: {args.roteiro}")
        if os.path.exists(args.roteiro):
            with open(args.roteiro, "r", encoding="utf-8") as f:
                roteiro_text = f.read().strip()
        else:
            print(f"[ERRO] Arquivo de roteiro não encontrado: {args.roteiro}")
            sys.exit(1)
    else:
        print("\n[OPCIONAL] Cole o texto do Roteiro de Narração para sincronização inteligente por IA:")
        print("(Pressione Ctrl+Z e depois Enter no Windows ou Ctrl+D no Linux/macOS em uma linha vazia para salvar, ou apenas dê Enter para pular):")
        
        roteiro_lines = []
        while True:
            try:
                line = input()
                roteiro_lines.append(line)
            except EOFError:
                break
                
        roteiro_text = "\n".join(roteiro_lines).strip()

    # Obter duração do áudio
    try:
        audio = AudioFileClip(audio_path)
        audio_duration = audio.duration
        audio.close()
    except Exception as e:
        print(f"[ERRO] Falha ao ler arquivo de áudio: {str(e)}")
        sys.exit(1)

    # Tenta obter a chave do DeepSeek e analisar o roteiro
    deepseek_key = load_deepseek_api_key()
    timeline = None
    if roteiro_text:
        timeline = analyze_script_timeline(deepseek_key, roteiro_text, audio_duration, audio_path)

    # Definir diretórios
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_dir = os.path.join(base_dir, "media", "videos", "temp")
    output_dir = os.path.join(base_dir, "media", "videos", "output")
    
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    output_filename = f"video_cinema_{int(time.time())}.mp4"
    output_path = os.path.join(output_dir, output_filename)

    video_temp_path = None
    try:
        # 1. Grava a tela do navegador
        video_temp_path, loading_duration = capture_video_recording(match_url, temp_dir, audio_duration, timeline)
        if not video_temp_path or not os.path.exists(video_temp_path):
            raise Exception("Não foi possível gerar a gravação de tela temporária do Playwright.")

        # 2. Mescla gravação + áudio narração
        merge_video_audio(video_temp_path, audio_path, output_path, loading_duration)

        print("\n" + "=" * 60)
        print("🎉 VÍDEO CINEMATOGRÁFICO GERADO COM SUCESSO!")
        print(f"Caminho do arquivo final: {output_path}")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERRO] Ocorreu uma falha durante o processo: {str(e)}")
    
    finally:
        if video_temp_path and os.path.exists(video_temp_path):
            print("\nLimpando gravação de tela temporária...")
            try:
                os.remove(video_temp_path)
                print("Limpeza concluída.")
            except Exception as e:
                print(f"[AVISO] Não foi possível apagar o vídeo temporário: {str(e)}")

    if not (args.url and args.audio):
        print("\nPressione Enter para fechar...")
        input()

if __name__ == "__main__":
    main()
