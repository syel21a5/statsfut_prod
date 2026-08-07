# ==============================================================
# VIDEO STUDIO (FÁBRICA DE VÍDEOS) - APENAS LOCALHOST
# ==============================================================
import os
import json
import time
import subprocess
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt

def is_localhost(request):
    host = request.META.get('HTTP_HOST', '')
    return host.startswith('127.0.0.1') or host.startswith('localhost')

class VideoStudioView(TemplateView):
    template_name = 'matches/video_studio.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not is_localhost(request) and not settings.DEBUG:
            return HttpResponseForbidden("Studio is only available on local development.")
        return super().dispatch(request, *args, **kwargs)

@csrf_exempt
def api_generate_video(request):
    if not is_localhost(request) and not settings.DEBUG:
        return JsonResponse({"error": "Forbidden"}, status=403)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            match_url = data.get('match_url')
            audio_path = data.get('audio_path', '').strip()
            roteiro_text = data.get('roteiro_text')
            format_type = data.get('format_type', 'long') # 'long' ou 'short'
            
            if not match_url or not roteiro_text:
                return JsonResponse({"error": "Faltam parâmetros obrigatórios (URL e Roteiro)."}, status=400)
                
            base_dir = settings.BASE_DIR
            videos_dir = os.path.join(base_dir, 'media', 'videos', 'temp')
            os.makedirs(videos_dir, exist_ok=True)
            
            if not audio_path:
                texto_limpo = roteiro_text.split("👇👇👇 TEXTO DA MÁQUINA")[0].replace("👇👇👇 TEXTO DO ÁUDIO (COPIE TUDO AQUI ABAIXO E COLE NO ELEVENLABS) 👇👇👇", "").strip()
                texto_limpo_path = os.path.join(videos_dir, 'roteiro_limpo_temp.txt')
                with open(texto_limpo_path, 'w', encoding='utf-8') as f:
                    f.write(texto_limpo)
                    
                import time
                audio_path = os.path.join(videos_dir, f'auto_audio_{int(time.time())}.mp3')
                rate = "+20%" if format_type == 'short' else "+0%"
                tts_cmd = [
                    "edge-tts",
                    "--voice", "pt-BR-AntonioNeural",
                    "--rate", rate,
                    "-f", texto_limpo_path,
                    "--write-media", audio_path
                ]
                subprocess.run(tts_cmd, check=True)
            
            roteiro_path = os.path.join(videos_dir, 'roteiro_temp.txt')
            with open(roteiro_path, 'w', encoding='utf-8') as f:
                f.write(roteiro_text)
                
            log_path = os.path.join(videos_dir, 'studio.log')
            
            # Limpa o log antigo
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write("[MÁQUINA] Iniciando processo na Fábrica de Vídeos...\n")
                
            script_name = "gerar_video.py" if format_type == 'long' else "gerar_video_curto.py"
            script_path = os.path.join(base_dir, "video_maker", script_name)
            
            import sys
            venv_python = sys.executable
                
            cmd = [
                venv_python, script_path,
                "--url", match_url,
                "--audio", audio_path,
                "--roteiro", roteiro_path
            ]
            
            # Dispara em background
            log_file = open(log_path, 'a', encoding='utf-8')
            subprocess.Popen(
                cmd,
                cwd=base_dir,
                stdout=log_file,
                stderr=subprocess.STDOUT
            )
            
            return JsonResponse({"status": "started"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
            
    return JsonResponse({"error": "Method not allowed"}, status=405)

def api_video_status(request):
    if not is_localhost(request) and not settings.DEBUG:
        return JsonResponse({"error": "Forbidden"}, status=403)
        
    log_path = os.path.join(settings.BASE_DIR, 'media', 'videos', 'temp', 'studio.log')
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Retorna as últimas 50 linhas para não travar
            content = "".join(lines[-50:])
            
            # Checar se finalizou
            is_finished = "VÍDEO CINEMATOGRÁFICO GERADO COM SUCESSO!" in content
            
            # Procurar o caminho final
            video_url = ""
            if is_finished:
                for line in reversed(lines):
                    if "Caminho do arquivo final:" in line:
                        path_str = line.split("Caminho do arquivo final:")[1].strip()
                        video_url = path_str
                        break
                        
            return JsonResponse({
                "log": content,
                "finished": is_finished,
                "video_url": video_url
            })
    return JsonResponse({"log": "Aguardando inicialização...", "finished": False})
