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
