"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns

from core.views import custom_set_language

# Rota de troca de idioma (sem prefixo, funciona de qualquer página)
urlpatterns = [
    path('i18n/setlang/', custom_set_language, name='set_language'),
    path('api/widgets/', include('widget_api.urls')),
]

from django.conf import settings

# Rotas com prefixo de idioma (/pt-br/, /es/, /de/) - inglês sem prefixo (/)
i18n_routes = [
    path('admin/', admin.site.urls),
    path('members/', include('members.urls')),
]

if 'video_maker' in settings.INSTALLED_APPS:
    i18n_routes.append(path('video-maker/', include('video_maker.urls')))

i18n_routes.append(path('', include('matches.urls')))

urlpatterns += i18n_patterns(
    *i18n_routes,
    prefix_default_language=False
)

from django.urls import re_path
from django.http import FileResponse, Http404
import os
from django.conf import settings

def serve_curated_image(request, filename_safe):
    # O Nginx intercepta qualquer URL com '.jpg'. Para evitar isso,
    # passamos a URL com '_dot_' no lugar do ponto.
    filename = filename_safe.replace("_dot_", ".")
    
    # Serve a imagem direto da pasta curated_images original na raiz do projeto
    path = os.path.join(settings.BASE_DIR, "curated_images", filename)
    if os.path.exists(path):
        return FileResponse(open(path, 'rb'))
    # Fallback para a pasta media ou static
    path2 = os.path.join(settings.BASE_DIR, "staticfiles", "curated_images", filename)
    if os.path.exists(path2):
        return FileResponse(open(path2, 'rb'))
    raise Http404("Imagem não encontrada")

# Forçar o Django a servir a pasta na web para o Blogger enxergar as imagens
urlpatterns += [
    path('imagens-blog/<str:filename_safe>', serve_curated_image),
]

# ── Servir arquivos de mídia (audios, vídeos, etc.) via Django ──
def serve_media_file(request, filepath):
    """Serve arquivos da pasta media/ (audios gerados, etc.) em produção."""
    full_path = os.path.join(settings.MEDIA_ROOT, filepath)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return FileResponse(open(full_path, 'rb'))
    raise Http404("Arquivo de mídia não encontrado")

from django.http import JsonResponse as DiagJsonResponse
def debug_media_check(request):
    """Temporário: diagnostica onde o MEDIA_ROOT está e se o arquivo existe."""
    media_root = str(settings.MEDIA_ROOT)
    base_dir = str(settings.BASE_DIR)
    audio_dir = os.path.join(media_root, 'audios_locucao')
    target_file = os.path.join(audio_dir, 'match_553270.mp3')
    
    # Também checa na raiz do projeto (caso MEDIA_ROOT estivesse vazio antes)
    alt_dir = os.path.join(base_dir, 'audios_locucao')
    alt_file = os.path.join(alt_dir, 'match_553270.mp3')
    
    result = {
        'MEDIA_ROOT': media_root,
        'BASE_DIR': base_dir,
        'audio_dir_exists': os.path.exists(audio_dir),
        'target_file_exists': os.path.exists(target_file),
        'alt_dir_exists': os.path.exists(alt_dir),
        'alt_file_exists': os.path.exists(alt_file),
    }
    
    if os.path.exists(audio_dir):
        result['audio_dir_files'] = os.listdir(audio_dir)
    if os.path.exists(alt_dir):
        result['alt_dir_files'] = os.listdir(alt_dir)
    
    # Procura o arquivo em qualquer lugar
    import subprocess
    try:
        find_result = subprocess.run(['find', base_dir, '-name', 'match_553270.mp3', '-type', 'f'], 
                                      capture_output=True, text=True, timeout=5)
        result['find_results'] = find_result.stdout.strip().split('\n') if find_result.stdout.strip() else []
    except:
        result['find_results'] = 'find command failed'
    
    return DiagJsonResponse(result)

urlpatterns += [
    re_path(r'^media/(?P<filepath>.+)$', serve_media_file),
    path('api/debug-media/', debug_media_check),
]

