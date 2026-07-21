import os
import time
from playwright.sync_api import sync_playwright
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips


def generate_match_video(url, audio_path, output_path):
    """
    Gera um vídeo vertical (9:16) a partir de screenshots da página de partida
    e um áudio narrado (ElevenLabs ou gravação manual).
    """
    shots_paths = []
    temp_dir = os.path.dirname(audio_path)  # reuse the temp dir
    os.makedirs(temp_dir, exist_ok=True)

    # 1. Capturar screenshots com Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 430, "height": 932})  # iPhone Pro Max

        page.goto(url, wait_until="networkidle", timeout=60000)

        # Remover overlays que possam atrapalhar
        page.evaluate("document.querySelectorAll('.video-script-modal, .modal-backdrop').forEach(e => e.remove());")
        time.sleep(1)

        # Shot 1: Cabeçalho da partida
        shot1 = os.path.join(temp_dir, f"shot1_{int(time.time())}.png")
        try:
            page.locator(".match-header").first.screenshot(path=shot1)
            shots_paths.append(shot1)
        except Exception:
            # Fallback: screenshot da página inteira
            page.screenshot(path=shot1)
            shots_paths.append(shot1)

        # Shot 2: Grade de probabilidades (Predictions)
        shot2 = os.path.join(temp_dir, f"shot2_{int(time.time())}.png")
        try:
            page.locator(".predictions-grid").first.screenshot(path=shot2)
            shots_paths.append(shot2)
        except Exception:
            pass  # pula se não encontrar

        # Shot 3: Aba de estatísticas (Corners/Shots)
        shot3 = os.path.join(temp_dir, f"shot3_{int(time.time())}.png")
        try:
            page.evaluate("typeof switchTab === 'function' && switchTab('stats')")
            time.sleep(1.5)
            page.locator("#stats-content").first.screenshot(path=shot3)
            shots_paths.append(shot3)
        except Exception:
            pass  # pula se não encontrar

        browser.close()

    if not shots_paths:
        raise Exception("Nenhum screenshot foi capturado da página. Verifique a URL da partida.")

    # 2. Montar o vídeo com MoviePy 2.x
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    # Duração por screenshot
    num_shots = len(shots_paths)
    duration_per_shot = total_duration / num_shots

    # Criar clips de imagem
    clips = []
    for shot_path in shots_paths:
        clip = (
            ImageClip(shot_path)
            .with_duration(duration_per_shot)
            .resized(width=1080)
        )
        clips.append(clip)

    # Concatenar e adicionar áudio
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.with_audio(audio)

    # Renderizar vídeo final
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4,
        logger="bar"
    )

    # Limpar screenshots temporários
    for path in shots_paths:
        if os.path.exists(path):
            os.remove(path)

    return output_path
