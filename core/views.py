import re
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import translation


def custom_set_language(request):
    """
    Custom set_language view that correctly translates URLs when 
    prefix_default_language=False is used. Django's default translate_url
    often fails to replace the prefix if the view is already resolved with one.
    """
    if request.method == 'POST':
        next_url = request.POST.get('next', '/')
        language = request.POST.get('language', settings.LANGUAGE_CODE)
    else:
        next_url = request.GET.get('next', '/')
        language = request.GET.get('language', settings.LANGUAGE_CODE)
        
    # Valida se o idioma existe nas configurações
    available_languages = [lang[0] for lang in settings.LANGUAGES]
    if language not in available_languages:
        language = settings.LANGUAGE_CODE
        
    translation.activate(language)
    
    # Remove qualquer prefixo de idioma existente na URL (ex: /es/stats/... -> /stats/...)
    prefix_pattern = r'^/(' + '|'.join(available_languages) + r')/'
    clean_url = re.sub(prefix_pattern, '/', next_url)
    
    # Se a nova linguagem não é o inglês (padrão sem prefixo), adiciona o novo prefixo
    if language != settings.LANGUAGE_CODE:
        if clean_url.startswith('/'):
            final_url = f'/{language}{clean_url}'
        else:
            final_url = f'/{language}/{clean_url}'
    else:
        final_url = clean_url
            
    response = HttpResponseRedirect(final_url)
    
    # Define o cookie
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        language,
        max_age=getattr(settings, 'LANGUAGE_COOKIE_AGE', 365 * 24 * 60 * 60),
        path=getattr(settings, 'LANGUAGE_COOKIE_PATH', '/'),
        domain=getattr(settings, 'LANGUAGE_COOKIE_DOMAIN', None),
        secure=getattr(settings, 'LANGUAGE_COOKIE_SECURE', False),
        httponly=getattr(settings, 'LANGUAGE_COOKIE_HTTPONLY', False),
        samesite=getattr(settings, 'LANGUAGE_COOKIE_SAMESITE', 'Lax'),
    )
    return response
