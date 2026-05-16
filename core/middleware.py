from django.utils import translation
from django.conf import settings


class ForceDefaultLanguageMiddleware:
    """
    Middleware que força o idioma padrão (inglês) para novos visitantes,
    ignorando o Accept-Language do navegador.
    
    Deve ser posicionado ANTES do LocaleMiddleware no MIDDLEWARE.
    
    Lógica:
    - Se o usuário já escolheu um idioma (cookie django_language), respeita.
    - Se a URL tem prefixo de idioma (/pt-br/, /es/), respeita.
    - Caso contrário, força o idioma padrão (en) ao invés de detectar do browser.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verifica se existe cookie de idioma (o usuário clicou na bandeirinha)
        cookie_lang = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        
        # Verifica se a URL tem prefixo de idioma
        url_lang = translation.get_language_from_path(request.path_info)
        
        if not cookie_lang and not url_lang:
            # Nenhuma escolha explícita: força o idioma padrão
            # Seta o cookie temporariamente no META para que o LocaleMiddleware
            # use o idioma padrão ao invés do Accept-Language
            request.META['HTTP_ACCEPT_LANGUAGE'] = settings.LANGUAGE_CODE
        
        response = self.get_response(request)
        return response
