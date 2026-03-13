import os
import sys
import django  # type: ignore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team  # type: ignore
from django.utils.text import slugify  # type: ignore
from django.conf import settings  # type: ignore

print("=== DIAGNÓSTICO DE LOGOS ===\n")

# Mostrar onde o Django procura por static files
print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
print(f"STATIC_URL: {settings.STATIC_URL}")
print(f"STATICFILES_DIRS: {getattr(settings, 'STATICFILES_DIRS', 'NÃO DEFINIDO')}\n")

# Caminhos de logo para ligas que funcionam vs. que não funcionam
countries_check = ['Suica', 'Belgica', 'Brasil', 'Austria', 'Franca', 'Australia']

for country in countries_check:
    leagues = League.objects.filter(country__icontains=country)
    for league in leagues:
        c_slug = slugify(league.country)
        l_slug = slugify(league.name)
        teams = Team.objects.filter(league=league, api_id__startswith='sofa_')[:2]
        
        for team in teams:
            logo_rel = f"teams/{c_slug}/{l_slug}/{team.api_id}.png"
            
            # Testa candidatos de paths no filesystem
            candidates = []
            if settings.STATIC_ROOT:
                candidates.append(os.path.join(settings.STATIC_ROOT, logo_rel))
            for d in getattr(settings, 'STATICFILES_DIRS', []):
                candidates.append(os.path.join(d, logo_rel))
            
            found = any(os.path.isfile(c) for c in candidates)
            status = "✓ EXISTE" if found else "✗ FALTANDO"
            print(f"[{country}] {status}: {logo_rel}")
            for c in candidates:
                ex = "✓" if os.path.isfile(c) else "✗"
                print(f"   {ex} {c}")
        break  # apenas uma liga por país
