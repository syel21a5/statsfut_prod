from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache

from .forms import CustomLoginForm, CustomRegisterForm
from .decorators import premium_required


@never_cache
def login_view(request):
    """Página de login com design premium dark."""
    if request.user.is_authenticated:
        return redirect('members:premium_dashboard')

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, _('Welcome back, %(username)s!') % {'username': user.username})
            next_url = request.GET.get('next', 'members:premium_dashboard')
            return redirect(next_url)
    else:
        form = CustomLoginForm()

    return render(request, 'members/login.html', {'form': form})


@never_cache
def register_view(request):
    """Página de registro com design premium dark."""
    if request.user.is_authenticated:
        return redirect('members:premium_dashboard')

    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _('Account created successfully! Welcome to StatsFut.'))
            return redirect('members:premium_dashboard')
    else:
        form = CustomRegisterForm()

    return render(request, 'members/register.html', {'form': form})


@require_POST
@never_cache
def logout_view(request):
    """Logout via POST (segurança CSRF)."""
    logout(request)
    messages.info(request, _('You have been logged out.'))
    return redirect('matches:home')


@login_required(login_url='members:login')
@never_cache
def profile_view(request):
    """Página de perfil do usuário."""
    return render(request, 'members/profile.html')


from django.db.models import Q
from matches.models import Match, League, Team, BetTicket
from django.utils import timezone
from datetime import timedelta
from zoneinfo import ZoneInfo

from matches.services.advanced_stats import MatchAnalyzer

@login_required(login_url='members:login')
@never_cache
def premium_dashboard(request):
    """Dashboard premium: Scanner Inteligente das Melhores Oportunidades do Dia."""
    is_premium = False
    if request.user.is_superuser or request.user.is_staff:
        is_premium = True
    elif hasattr(request.user, 'profile'):
        is_premium = request.user.profile.is_premium_active

    br_tz = ZoneInfo('America/Sao_Paulo')
    now_br = timezone.now().astimezone(br_tz)
    start_of_day = now_br.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_of_day + timedelta(days=2) # Hoje e Amanhã
    
    matches = Match.objects.filter(
        date__range=(start_of_day, end_date),
        status__in=['NS', 'Not Started', 'Scheduled', 'TBD', 'POSTPONED', 'Postponed'] # Apenas jogos não iniciados
    ).select_related('league', 'home_team', 'away_team').order_by('date')[:100]
    
    # Se não for premium, manda apenas os jogos crus para gerar a tela "borrada" de marketing
    if not is_premium:
        context = {
            'is_premium': False,
            'upcoming_matches': matches[:15],
        }
        return render(request, 'members/premium_dashboard.html', context)

    # Buscar Bilhetes Prontos (Estratégias)
    active_tickets = BetTicket.objects.filter(
        status='Pending'
    ).prefetch_related('selections__match__home_team', 'selections__match__away_team', 'selections__match__league')
    
    history_tickets = BetTicket.objects.filter(
        status__in=['Green', 'Red']
    ).prefetch_related('selections__match__home_team', 'selections__match__away_team', 'selections__match__league')[:10]

    # Listas do Scanner de Gols
    high_ht_goals = []
    high_over15 = []
    high_over25 = []
    high_btts = []
    
    # Listas de Vencedor / Primeiro a Marcar
    high_win = []
    first_to_score = []
    
    # Listas Extras
    high_corners = []
    
    for m in matches:
        try:
            analyzer = MatchAnalyzer(m)
            goals = analyzer.get_goal_markets()
            corners = analyzer.get_corner_markets()
            odds = analyzer.get_match_odds_probs()
            
            # Match data helper
            match_data = {
                'match': m,
                'ht_goal': goals.get('ht_goal', 0),
                'over_15': goals.get('over_15', 0),
                'over_25': goals.get('over_25', 0),
                'btts': goals.get('btts', 0),
                'home_first': goals.get('home_first_score', 0),
                'away_first': goals.get('away_first_score', 0),
                'home_win': odds.get('home_win', 0),
                'away_win': odds.get('away_win', 0),
            }
            
            # --- MERCADO DE GOLS ---
            if match_data['ht_goal'] >= 75:
                high_ht_goals.append(match_data)
            if match_data['over_15'] >= 80:
                high_over15.append(match_data)
            if match_data['over_25'] >= 65:
                high_over25.append(match_data)
            if match_data['btts'] >= 65:
                high_btts.append(match_data)
                
            # --- VENCEDOR (Match Odds > 65%) ---
            if match_data['home_win'] >= 65:
                high_win.append({**match_data, 'team_to_win': m.home_team.name, 'prob': match_data['home_win']})
            elif match_data['away_win'] >= 65:
                high_win.append({**match_data, 'team_to_win': m.away_team.name, 'prob': match_data['away_win']})
                
            # --- PRIMEIRO A MARCAR (> 75%) ---
            if match_data['home_first'] >= 75:
                first_to_score.append({**match_data, 'team_first': m.home_team.name, 'prob': match_data['home_first']})
            elif match_data['away_first'] >= 75:
                first_to_score.append({**match_data, 'team_first': m.away_team.name, 'prob': match_data['away_first']})
                
            # --- CANTOS (Over 9.5 > 70%) ---
            if corners.get('match_overs', {}).get(9, 0) >= 70:
                high_corners.append({
                    'match': m,
                    'prob': corners['match_overs'][9],
                    'line': 'Over 9.5'
                })
        except Exception as e:
            # Silently ignore games that lack enough data for calculation
            continue

    # Ordenações
    high_ht_goals.sort(key=lambda x: x['ht_goal'], reverse=True)
    high_over15.sort(key=lambda x: x['over_15'], reverse=True)
    high_over25.sort(key=lambda x: x['over_25'], reverse=True)
    high_btts.sort(key=lambda x: x['btts'], reverse=True)
    high_win.sort(key=lambda x: x['prob'], reverse=True)
    first_to_score.sort(key=lambda x: x['prob'], reverse=True)
    high_corners.sort(key=lambda x: x['prob'], reverse=True)

    context = {
        'is_premium': True,
        'high_ht_goals': high_ht_goals,
        'high_over15': high_over15,
        'high_over25': high_over25,
        'high_btts': high_btts,
        'high_win': high_win,
        'first_to_score': first_to_score,
        'high_corners': high_corners,
        'active_tickets': active_tickets,
        'history_tickets': history_tickets,
        'total_scanned': len(matches),
        'total_opportunities': len(high_ht_goals) + len(high_over15) + len(high_over25) + len(high_btts) + len(high_win) + len(first_to_score) + len(high_corners),
    }
    return render(request, 'members/premium_dashboard.html', context)


@never_cache
def paywall_view(request):
    """Página que mostra os planos para quem não é premium."""
    return render(request, 'members/paywall.html')
