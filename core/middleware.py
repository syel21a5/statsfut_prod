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


class CloudflareCacheControlMiddleware:
    """
    Middleware que impede o Cloudflare de cachear páginas de usuários autenticados.
    
    Problema: O Cloudflare cacheia a página HTML com o header do usuário logado
    (mostrando nome, dropdown, etc). Após o logout, ele serve essa versão cacheada,
    fazendo parecer que o usuário ainda está logado. Ao clicar em Premium (que tem
    @never_cache), aí sim o Django percebe que não há sessão e pede login.
    
    Solução:
    - Para usuários AUTENTICADOS: Cache-Control: no-store (nunca cachear)
    - Para TODOS: Vary: Cookie (CDN trata logado vs deslogado como respostas diferentes)
    - Após LOGOUT: o sessionid é apagado, então o Cloudflare serve conteúdo de visitante
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Não mexer em arquivos estáticos (CSS, JS, imagens, fontes)
        path = request.path
        static_prefixes = ('/static/', '/media/', '/favicon.ico')
        if any(path.startswith(p) for p in static_prefixes):
            return response

        # Adiciona Vary: Cookie para que o Cloudflare diferencie
        # respostas de usuários logados vs visitantes
        if 'Vary' in response:
            if 'Cookie' not in response['Vary']:
                response['Vary'] += ', Cookie'
        else:
            response['Vary'] = 'Cookie'

        # Se o usuário está autenticado, impedir cache completamente
        if hasattr(request, 'user') and request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response
