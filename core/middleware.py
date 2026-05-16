from django.middleware.locale import LocaleMiddleware
from django.conf import settings
from django.utils import translation


class ExplicitLocaleMiddleware(LocaleMiddleware):
    """
    Middleware de idioma customizado que IGNORA o header Accept-Language do navegador.
    
    O idioma só muda quando o usuário clica na bandeirinha (que define o cookie 'django_language')
    ou quando o prefixo está explícito na URL (/pt-br/, /es/, /de/).
    
    Se não houver cookie nem prefixo, usa o idioma padrão (LANGUAGE_CODE = 'en').
    Isso garante que o site sempre inicie em inglês para novos visitantes.
    """

    def process_request(self, request):
        # 1. Verifica se o idioma está na URL (/pt-br/, /es/, /de/)
        url_lang = translation.get_language_from_path(request.path_info)
        
        # 2. Verifica se o usuário escolheu um idioma explicitamente (cookie da bandeirinha)
        cookie_lang = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        
        if url_lang:
            # Idioma explícito na URL -> respeita
            language = url_lang
        elif cookie_lang:
            # Usuário escolheu via bandeirinha -> respeita o cookie
            language = cookie_lang
        else:
            # Nenhuma escolha explícita -> idioma padrão (inglês)
            # NÃO detecta o Accept-Language do navegador
            language = settings.LANGUAGE_CODE
        
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
