from django.views.generic import TemplateView
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, FileResponse
import os
import threading
import time

# Lazy load so we don't break if dependencies fail
try:
    from .video_generator import generate_match_video
except ImportError:
    generate_match_video = None

class VideoMakerView(TemplateView):
    template_name = 'video_maker/video_maker.html'

    def post(self, request, *args, **kwargs):
        if not generate_match_video:
            return HttpResponse("Video generation modules not installed properly. Check playwright/moviepy.", status=500)

        match_url = request.POST.get('match_url')
        audio_file = request.FILES.get('audio_file')
        
        if not match_url or not audio_file:
            return render(request, self.template_name, {'error': 'URL da partida e arquivo de áudio são obrigatórios!'})

        # Save audio file temporarily
        fs = FileSystemStorage(location='media/videos/temp')
        filename = fs.save(audio_file.name, audio_file)
        audio_path = fs.path(filename)
        
        # Define output path
        timestamp = int(time.time())
        output_filename = f'video_match_{timestamp}.mp4'
        output_dir = os.path.abspath('media/videos/output')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)

        try:
            # Generate the video
            generate_match_video(match_url, audio_path, output_path)
            
            # Clean up temp audio
            if os.path.exists(audio_path):
                os.remove(audio_path)
                
            # Return the video for download
            return FileResponse(open(output_path, 'rb'), as_attachment=True, filename=output_filename)
            
        except Exception as e:
            if os.path.exists(audio_path):
                os.remove(audio_path)
            return render(request, self.template_name, {'error': f'Erro ao gerar vídeo: {str(e)}'})

