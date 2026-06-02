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


@never_cache
@login_required(login_url='members:login')
def profile_view(request):
    """Página de perfil do usuário."""
    return render(request, 'members/profile.html')


from django.db.models import Q
from matches.models import Match, League, Team, BetTicket
from django.utils import timezone
from datetime import timedelta
from zoneinfo import ZoneInfo

from matches.services.advanced_stats import MatchAnalyzer

@never_cache
@login_required(login_url='members:login')
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

    # ----------------- ROBÔ DE AVALIAÇÃO EM TEMPO REAL -----------------
    from matches.models import ScannerTip, Goal
    
    # 1. Avaliar Dicas do Scanner Inteligente
    #    Inclui PENDING (normal) + GREEN/RED recentes (re-avaliação caso placar mude)
    finished_statuses = ['FT', 'Finished', 'AET', 'PEN', 'Match Finished']
    three_days_ago = timezone.now() - timedelta(days=3)
    
    tips_to_resolve = ScannerTip.objects.filter(
        match__status__in=finished_statuses,
        match__date__gte=three_days_ago
    ).select_related('match')
    
    for tip in tips_to_resolve:
        m = tip.match
        if m.home_score is None or m.away_score is None:
            continue
        total_goals = m.home_score + m.away_score
        is_green = False
        
        try:
            if tip.market == 'HT_GOAL':
                goals_ht = m.goals.filter(minute__lte=45).exists()
                is_green = goals_ht
            elif tip.market == 'HT_GOALS_NOT_2_4':
                if m.ht_home_score is not None and m.ht_away_score is not None:
                    ht_g = m.ht_home_score + m.ht_away_score
                    is_green = not (2 <= ht_g <= 4)
                else:
                    goals_ht_count = m.goals.filter(minute__lte=45).count()
                    is_green = not (2 <= goals_ht_count <= 4)
            elif tip.market == 'SH_GOALS_NOT_2_4':
                if m.ht_home_score is not None and m.ht_away_score is not None and m.home_score is not None and m.away_score is not None:
                    sh_g = (m.home_score + m.away_score) - (m.ht_home_score + m.ht_away_score)
                    is_green = not (2 <= sh_g <= 4)
                else:
                    goals_sh_count = m.goals.filter(minute__gt=45).count()
                    is_green = not (2 <= goals_sh_count <= 4)
            elif tip.market.startswith('DC_1X_UNDER_'):
                line = float(tip.market.split('_')[-1]) / 10.0
                has_dc = m.home_score >= m.away_score
                has_under = total_goals < line
                is_green = has_dc and has_under
            elif tip.market.startswith('DC_X2_UNDER_'):
                line = float(tip.market.split('_')[-1]) / 10.0
                has_dc = m.away_score >= m.home_score
                has_under = total_goals < line
                is_green = has_dc and has_under
            elif tip.market == 'OVER_05':
                is_green = total_goals >= 1
            elif tip.market == 'OVER_15':
                is_green = total_goals >= 2
            elif tip.market == 'OVER_25':
                is_green = total_goals >= 3
            elif tip.market == 'OVER_35':
                is_green = total_goals >= 4
            elif tip.market == 'UNDER_35':
                is_green = total_goals <= 3
            elif tip.market == 'UNDER_45':
                is_green = total_goals <= 4
            elif tip.market == 'UNDER_55':
                is_green = total_goals <= 5
            elif tip.market == 'UNDER_65':
                is_green = total_goals <= 6
            elif tip.market == 'BTTS':
                is_green = (m.home_score > 0 and m.away_score > 0)
            elif tip.market == 'HOME_WIN':
                is_green = m.home_score > m.away_score
            elif tip.market == 'AWAY_WIN':
                is_green = m.away_score > m.home_score
            elif tip.market == 'DC_1X':
                is_green = m.home_score >= m.away_score
            elif tip.market == 'DC_X2':
                is_green = m.away_score >= m.home_score
            elif tip.market == 'DNB_HOME':
                is_green = m.home_score > m.away_score
            elif tip.market == 'DNB_AWAY':
                is_green = m.away_score > m.home_score
            elif tip.market == 'FIRST_SCORE_HOME':
                first_goal = m.goals.order_by('minute').first()
                if first_goal:
                    is_green = first_goal.team_id == m.home_team_id
                else:
                    is_green = m.home_score > 0 and m.away_score == 0
            elif tip.market == 'FIRST_SCORE_AWAY':
                first_goal = m.goals.order_by('minute').first()
                if first_goal:
                    is_green = first_goal.team_id == m.away_team_id
                else:
                    is_green = m.away_score > 0 and m.home_score == 0
            elif tip.market.startswith('CORNERS_OVER_'):
                if m.home_corners is not None and m.away_corners is not None:
                    try:
                        line = float(tip.market.split('_')[-1]) / 10.0
                    except ValueError:
                        line = 9.5
                    is_green = (m.home_corners + m.away_corners) > line
                else:
                    continue
            elif tip.market == 'CORNER_WIN_H':
                if m.home_corners is not None and m.away_corners is not None:
                    is_green = m.home_corners > m.away_corners
                else:
                    continue
            elif tip.market == 'CORNER_WIN_A':
                if m.home_corners is not None and m.away_corners is not None:
                    is_green = m.away_corners > m.home_corners
                else:
                    continue
            elif tip.market.startswith('CARDS_OVER_'):
                if m.home_yellow is not None and m.away_yellow is not None:
                    try:
                        line = float(tip.market.split('_')[-1]) / 10.0
                    except ValueError:
                        line = 4.5
                    is_green = (m.home_yellow + m.away_yellow) > line
                else:
                    continue
            elif tip.market == 'CARD_WIN_H':
                if m.home_yellow is not None and m.away_yellow is not None:
                    is_green = m.home_yellow > m.away_yellow
                else:
                    continue
            elif tip.market == 'CARD_WIN_A':
                if m.home_yellow is not None and m.away_yellow is not None:
                    is_green = m.away_yellow > m.home_yellow
                else:
                    continue
            else:
                continue

            new_status = 'GREEN' if is_green else 'RED'
            if tip.status != new_status:
                tip.status = new_status
                tip.save(update_fields=['status', 'updated_at'])
        except Exception:
            pass

    # 2. Avaliar Bilhetes Pendentes (Estratégias Prontas)
    pending_tickets_to_resolve = BetTicket.objects.filter(status='Pending')
    for ticket in pending_tickets_to_resolve:
        selections = ticket.selections.all()
        all_resolved = True
        any_red = False
        any_pending = False

        for sel in selections:
            m = sel.match
            is_finished = m.status in ['FT', 'Finished', 'Concluded'] or (m.home_score is not None and m.away_score is not None)
            
            if not is_finished:
                any_pending = True
                all_resolved = False
                continue

            home_score = m.home_score or 0
            away_score = m.away_score or 0
            total_goals = home_score + away_score
            ht_home = m.ht_home_score or 0
            ht_away = m.ht_away_score or 0
            ht_goals = ht_home + ht_away

            result = 'Pending'

            if sel.prediction_market == 'over_15':
                result = 'Green' if total_goals >= 2 else 'Red'
            elif sel.prediction_market == 'ht_goal':
                result = 'Green' if ht_goals >= 1 else 'Red'
            elif sel.prediction_market == 'over_25':
                result = 'Green' if total_goals >= 3 else 'Red'
            elif sel.prediction_market == 'over_05':
                result = 'Green' if total_goals >= 1 else 'Red'
            elif sel.prediction_market == 'under_35':
                result = 'Green' if total_goals <= 3 else 'Red'
            elif sel.prediction_market == 'btts':
                result = 'Green' if (home_score > 0 and away_score > 0) else 'Red'
            elif sel.prediction_market == 'btts_no':
                result = 'Green' if not (home_score > 0 and away_score > 0) else 'Red'
            elif sel.prediction_market == 'home_win':
                result = 'Green' if home_score > away_score else 'Red'
            elif sel.prediction_market == 'away_win':
                result = 'Green' if away_score > home_score else 'Red'
            elif sel.prediction_market == 'double_chance_1x':
                result = 'Green' if home_score >= away_score else 'Red'
            elif sel.prediction_market == 'double_chance_x2':
                result = 'Green' if away_score >= home_score else 'Red'
            elif sel.prediction_market == 'over_95_corners':
                if m.home_corners is not None and m.away_corners is not None:
                    result = 'Green' if (m.home_corners + m.away_corners) >= 10 else 'Red'
                else:
                    result = 'Void'
            elif sel.prediction_market == 'home_first':
                first_goal = Goal.objects.filter(match=m).order_by('minute').first()
                if first_goal:
                    result = 'Green' if first_goal.team == m.home_team else 'Red'
                else:
                    result = 'Green' if home_score > 0 and away_score == 0 else 'Red'
            elif sel.prediction_market == 'away_first':
                first_goal = Goal.objects.filter(match=m).order_by('minute').first()
                if first_goal:
                    result = 'Green' if first_goal.team == m.away_team else 'Red'
                else:
                    result = 'Green' if away_score > 0 and home_score == 0 else 'Red'
            else:
                result = 'Void'

            if sel.status != result:
                sel.status = result
                sel.save(update_fields=['status'])

            if result == 'Red':
                any_red = True

        if any_red:
            ticket.status = 'Red'
            ticket.save(update_fields=['status'])
        elif not any_pending and all_resolved:
            ticket.status = 'Green'
            ticket.save(update_fields=['status'])

    # Buscar Bilhetes Prontos (Estratégias) - Atualizados em tempo real e ordenados por tipo!
    active_tickets = BetTicket.objects.filter(
        status='Pending'
    ).prefetch_related('selections__match__home_team', 'selections__match__away_team', 'selections__match__league').order_by('-ticket_type', '-created_at')
    
    history_tickets = BetTicket.objects.filter(
        status__in=['Green', 'Red']
    ).prefetch_related('selections__match__home_team', 'selections__match__away_team', 'selections__match__league').order_by('-ticket_type', '-created_at')[:10]

    # Buscar dicas pendentes para os próximos 3 dias
    pending_tips = ScannerTip.objects.filter(
        status='PENDING',
        match__date__range=(start_of_day, end_date + timedelta(days=1))
    ).select_related('match', 'match__league', 'match__home_team', 'match__away_team').order_by('match__date')
    
    # Buscar histórico de dicas dos últimos 7 dias (GREEN, RED, e PENDING de jogos finalizados)
    seven_days_ago = timezone.now() - timedelta(days=7)
    evaluated_tips = ScannerTip.objects.filter(
        status__in=['GREEN', 'RED'],
        match__date__gte=seven_days_ago
    ).select_related('match', 'match__league', 'match__home_team', 'match__away_team').order_by('-match__date')
    
    # Incluir PENDING de jogos já finalizados (para que não desapareçam do histórico)
    pending_finished_tips = ScannerTip.objects.filter(
        status='PENDING',
        match__status__in=finished_statuses,
        match__date__gte=seven_days_ago
    ).select_related('match', 'match__league', 'match__home_team', 'match__away_team').order_by('-match__date')
    
    # Combinar as duas querysets
    from itertools import chain
    all_history_tips = list(chain(evaluated_tips, pending_finished_tips))

    # Mapeamento de mercados para categorias
    GOALS_MARKETS = {'HT_GOAL', 'OVER_05', 'OVER_15', 'OVER_25', 'OVER_35', 'UNDER_35', 'UNDER_45', 'UNDER_55', 'UNDER_65', 'HT_GOALS_NOT_2_4', 'SH_GOALS_NOT_2_4'}
    BTTS_MARKETS = {'BTTS', 'BTTS_1H', 'BTTS_2H', 'BTTS_BOTH'}
    RESULT_MARKETS = {'HOME_WIN', 'AWAY_WIN', 'DC_1X', 'DC_X2', 'DNB_HOME', 'DNB_AWAY', 'FIRST_SCORE_HOME', 'FIRST_SCORE_AWAY', 'HT_HOME_WIN', 'HT_AWAY_WIN'}
    SPECIALS_MARKETS = {'HOME_CS', 'AWAY_CS', 'HOME_WTN', 'AWAY_WTN', 'HC_HOME_M05', 'HC_HOME_M15', 'HC_AWAY_P15', 'MARGIN_H1', 'MARGIN_H2', 'WIN_BTTS_HY', 'WIN_BTTS_AY', 'WIN_BTTS_HN', 'MOST_1H', 'MOST_2H'}
    CORNERS_MARKETS = {'CORNERS_OVER_75', 'CORNERS_OVER_85', 'CORNERS_OVER_95', 'CORNERS_OVER_105', 'CORNERS_OVER_115', 'CORNER_WIN_H', 'CORNER_WIN_A'}
    CARDS_MARKETS = {'CARDS_OVER_35', 'CARDS_OVER_45', 'CARDS_OVER_55', 'CARDS_OVER_65', 'CARD_WIN_H', 'CARD_WIN_A'}
    SHOTS_MARKETS = {'SHOTS_OVER_205', 'SHOTS_OVER_225', 'SHOTS_OVER_245', 'SOT_OVER_65', 'SOT_OVER_75', 'SOT_OVER_85', 'SHOT_WIN_H', 'SHOT_WIN_A'}
    
    def get_date_group(match_date):
        if not match_date: return _("Future")
        match_date_br = match_date.astimezone(br_tz).date()
        today = now_br.date()
        diff = (match_date_br - today).days
        if diff == 0: return _("Today")
        elif diff == 1: return _("Tomorrow")
        elif diff == 2: return _("Day After Tomorrow")
        return match_date_br.strftime("%d/%m")

    # Containers for each category
    tips_goals = []
    tips_btts = []
    tips_result = []
    tips_specials = []
    tips_corners = []
    tips_cards = []
    tips_shots = []
    tips_dc_over = []
    tips_dc_btts = []

    def get_translated_text(tip):
        m = tip.market
        home = tip.match.home_team.name
        away = tip.match.away_team.name
        
        # Goals
        if m == 'HT_GOAL': return _("Goal in 1st Half (HT)")
        elif m == 'HT_GOALS_NOT_2_4': return _("Not 2-4 Goals in 1st Half (HT)")
        elif m == 'SH_GOALS_NOT_2_4': return _("Not 2-4 Goals in 2nd Half (2T)")
        elif m.startswith('DC_1X_UNDER_'):
            line = m.replace('DC_1X_UNDER_', '').replace('_', '.')
            return _("Casa ou Empate & Menos de %(line)s Gols") % {'line': line}
        elif m.startswith('DC_X2_UNDER_'):
            line = m.replace('DC_X2_UNDER_', '').replace('_', '.')
            return _("Empate ou Fora & Menos de %(line)s Gols") % {'line': line}
        elif m.startswith('DC_1X_OVER_'):
            line = m.replace('DC_1X_OVER_', '').replace('_', '.')
            return _("Casa ou Empate & Mais de %(line)s Gols") % {'line': line}
        elif m.startswith('DC_X2_OVER_'):
            line = m.replace('DC_X2_OVER_', '').replace('_', '.')
            return _("Empate ou Fora & Mais de %(line)s Gols") % {'line': line}
        elif m == 'DC_1X_BTTS_YES':
            return _("Casa ou Empate & Ambas Marcam Sim")
        elif m == 'DC_1X_BTTS_NO':
            return _("Casa ou Empate & Ambas Marcam Não")
        elif m == 'DC_X2_BTTS_YES':
            return _("Empate ou Fora & Ambas Marcam Sim")
        elif m == 'DC_X2_BTTS_NO':
            return _("Empate ou Fora & Ambas Marcam Não")
        elif m == 'OVER_05': return _("Over 0.5 Goals")
        elif m == 'OVER_15': return _("Over 1.5 Goals")
        elif m == 'OVER_25': return _("Over 2.5 Goals")
        elif m == 'OVER_35': return _("Over 3.5 Goals")
        elif m == 'UNDER_35': return _("Under 3.5 Goals")
        elif m == 'UNDER_45': return _("Under 4.5 Goals")
        elif m == 'UNDER_55': return _("Under 5.5 Goals")
        elif m == 'UNDER_65': return _("Under 6.5 Goals")
        # BTTS
        elif m == 'BTTS': return _("Both Teams to Score")
        elif m == 'BTTS_1H': return _("BTTS 1st Half")
        elif m == 'BTTS_2H': return _("BTTS 2nd Half")
        elif m == 'BTTS_BOTH': return _("BTTS Both Halves")
        # Result
        elif m == 'HOME_WIN': return _("%(team)s to Win") % {'team': home}
        elif m == 'AWAY_WIN': return _("%(team)s to Win") % {'team': away}
        elif m == 'DC_1X': return _("Double Chance 1X (%(team)s or Draw)") % {'team': home}
        elif m == 'DC_X2': return _("Double Chance X2 (Draw or %(team)s)") % {'team': away}
        elif m == 'DNB_HOME': return _("Draw No Bet - %(team)s") % {'team': home}
        elif m == 'DNB_AWAY': return _("Draw No Bet - %(team)s") % {'team': away}
        elif m == 'FIRST_SCORE_HOME': return _("%(team)s to Score First") % {'team': home}
        elif m == 'FIRST_SCORE_AWAY': return _("%(team)s to Score First") % {'team': away}
        elif m == 'HT_HOME_WIN': return _("%(team)s Leading at HT") % {'team': home}
        elif m == 'HT_AWAY_WIN': return _("%(team)s Leading at HT") % {'team': away}
        # Specials
        elif m == 'HOME_CS': return _("%(team)s Clean Sheet") % {'team': home}
        elif m == 'AWAY_CS': return _("%(team)s Clean Sheet") % {'team': away}
        elif m == 'HOME_WTN': return _("%(team)s Win to Nil") % {'team': home}
        elif m == 'AWAY_WTN': return _("%(team)s Win to Nil") % {'team': away}
        elif m == 'HC_HOME_M05': return _("%(team)s -0.5 (AH)") % {'team': home}
        elif m == 'HC_HOME_M15': return _("%(team)s -1.5 (AH)") % {'team': home}
        elif m == 'HC_AWAY_P15': return _("%(team)s +1.5 (AH)") % {'team': away}
        elif m == 'MARGIN_H1': return _("%(team)s Wins by 1 Goal") % {'team': home}
        elif m == 'MARGIN_H2': return _("%(team)s Wins by 2 Goals") % {'team': home}
        elif m == 'WIN_BTTS_HY': return _("%(team)s Win & BTTS Yes") % {'team': home}
        elif m == 'WIN_BTTS_AY': return _("%(team)s Win & BTTS Yes") % {'team': away}
        elif m == 'WIN_BTTS_HN': return _("%(team)s Win & BTTS No") % {'team': home}
        elif m == 'MOST_1H': return _("1st Half Most Goals")
        elif m == 'MOST_2H': return _("2nd Half Most Goals")
        # Corners
        elif m == 'CORNERS_OVER_75': return _("Over 7.5 Corners")
        elif m == 'CORNERS_OVER_85': return _("Over 8.5 Corners")
        elif m == 'CORNERS_OVER_95': return _("Over 9.5 Corners")
        elif m == 'CORNERS_OVER_105': return _("Over 10.5 Corners")
        elif m == 'CORNERS_OVER_115': return _("Over 11.5 Corners")
        elif m == 'CORNER_WIN_H': return _("%(team)s Wins Corners") % {'team': home}
        elif m == 'CORNER_WIN_A': return _("%(team)s Wins Corners") % {'team': away}
        # Cards
        elif m == 'CARDS_OVER_35': return _("Over 3.5 Cards")
        elif m == 'CARDS_OVER_45': return _("Over 4.5 Cards")
        elif m == 'CARDS_OVER_55': return _("Over 5.5 Cards")
        elif m == 'CARDS_OVER_65': return _("Over 6.5 Cards")
        elif m == 'CARD_WIN_H': return _("%(team)s Most Cards") % {'team': home}
        elif m == 'CARD_WIN_A': return _("%(team)s Most Cards") % {'team': away}
        # Shots
        elif m == 'SHOTS_OVER_205': return _("Over 20.5 Total Shots")
        elif m == 'SHOTS_OVER_225': return _("Over 22.5 Total Shots")
        elif m == 'SHOTS_OVER_245': return _("Over 24.5 Total Shots")
        elif m == 'SOT_OVER_65': return _("Over 6.5 Shots on Target")
        elif m == 'SOT_OVER_75': return _("Over 7.5 Shots on Target")
        elif m == 'SOT_OVER_85': return _("Over 8.5 Shots on Target")
        elif m == 'SHOT_WIN_H': return _("%(team)s More Shots") % {'team': home}
        elif m == 'SHOT_WIN_A': return _("%(team)s More Shots") % {'team': away}
        
        return _(tip.prediction_text)

    for tip in pending_tips:
        item = {
            'match': tip.match,
            'prob': tip.probability,
            'odd': tip.odd,
            'text': get_translated_text(tip),
            'market': tip.market,
            'date_group': get_date_group(tip.match.date),
            'sort_date': tip.match.date,
        }
        
        if tip.market in GOALS_MARKETS or tip.market.startswith('DC_1X_UNDER_') or tip.market.startswith('DC_X2_UNDER_'):
            tips_goals.append(item)
        elif tip.market in BTTS_MARKETS:
            tips_btts.append(item)
        elif tip.market in RESULT_MARKETS:
            tips_result.append(item)
        elif tip.market in SPECIALS_MARKETS:
            tips_specials.append(item)
        elif tip.market in CORNERS_MARKETS:
            tips_corners.append(item)
        elif tip.market in CARDS_MARKETS:
            tips_cards.append(item)
        elif tip.market in SHOTS_MARKETS:
            tips_shots.append(item)
        elif tip.market.startswith('DC_1X_OVER_') or tip.market.startswith('DC_X2_OVER_'):
            tips_dc_over.append(item)
        elif tip.market.startswith('DC_1X_BTTS_') or tip.market.startswith('DC_X2_BTTS_'):
            tips_dc_btts.append(item)

    history_groups = {
        'goals': [],
        'btts': [],
        'corners': [],
        'cards': [],
        'shots': [],
        'outcomes': [],
        'specials': []
    }
    history_stats_by_market = {}

    for tip in all_history_tips:
        m_type = tip.market
        
        group_key = 'outros'
        if m_type in GOALS_MARKETS or m_type.startswith('DC_1X_UNDER_') or m_type.startswith('DC_X2_UNDER_'): group_key = 'goals'
        elif m_type in BTTS_MARKETS: group_key = 'btts'
        elif m_type in CORNERS_MARKETS: group_key = 'corners'
        elif m_type in CARDS_MARKETS: group_key = 'cards'
        elif m_type in SHOTS_MARKETS: group_key = 'shots'
        elif m_type in RESULT_MARKETS: group_key = 'outcomes'
        elif m_type in SPECIALS_MARKETS: group_key = 'specials'

        item = {
            'match': tip.match,
            'prob': tip.probability,
            'text': get_translated_text(tip),
            'status': tip.status,
            'date': tip.match.date,
            'market': tip.market,
            'category': group_key,
        }
        
        if group_key in history_groups:
            history_groups[group_key].append(item)

        # Só contabilizar GREEN/RED nas estatísticas (PENDING não entra)
        if tip.status in ('GREEN', 'RED'):
            if m_type not in history_stats_by_market:
                history_stats_by_market[m_type] = {'green': 0, 'red': 0, 'total': 0, 'win_rate': 0}
            history_stats_by_market[m_type]['total'] += 1
            if tip.status == 'GREEN':
                history_stats_by_market[m_type]['green'] += 1
            elif tip.status == 'RED':
                history_stats_by_market[m_type]['red'] += 1

    for m_type, stats in history_stats_by_market.items():
        stats['win_rate'] = int((stats['green'] / stats['total']) * 100) if stats['total'] > 0 else 0

    for key in history_groups:
        history_groups[key].sort(key=lambda x: x['prob'], reverse=True)


    # Calcular assertividade por data (Geral + Por Dia)
    stats_by_date = {'Geral': {}}
    market_labels = {
        'HT_GOAL': 'HT Goal',
        'OVER_05': 'Over 0.5 Goals',
        'OVER_15': 'Over 1.5 Goals',
        'OVER_25': 'Over 2.5 Goals',
        'OVER_35': 'Over 3.5 Goals',
        'UNDER_35': 'Under 3.5 Goals',
        'UNDER_45': 'Under 4.5 Goals',
        'UNDER_55': 'Under 5.5 Goals',
        'UNDER_65': 'Under 6.5 Goals',
        'BTTS': 'Both Teams to Score',
    }

    def get_market_group(m_type):
        if m_type in market_labels:
            return market_labels[m_type]
        elif m_type.startswith('CORNERS_') or m_type.startswith('CORNER_'):
            return 'Corners'
        elif m_type.startswith('CARDS_') or m_type.startswith('CARD_'):
            return 'Cards'
        elif m_type.startswith('SHOTS_') or m_type.startswith('SOT_') or m_type.startswith('SHOT_'):
            return 'Shots'
        elif m_type in ['HOME_WIN', 'AWAY_WIN', 'DC_1X', 'DC_X2', 'DNB_HOME', 'DNB_AWAY', 'FIRST_SCORE_HOME', 'FIRST_SCORE_AWAY']:
            return 'Outcomes'
        return 'Outros'

    for tip in evaluated_tips:
        m_type = tip.market
        status = tip.status
        group_key = get_market_group(m_type)
        
        # Data local da partida formatada (DD/MM)
        date_str = tip.match.date.astimezone(br_tz).strftime('%d/%m')
        
        if date_str not in stats_by_date:
            stats_by_date[date_str] = {}
            
        for target in ['Geral', date_str]:
            if group_key not in stats_by_date[target]:
                stats_by_date[target][group_key] = {'green': 0, 'total': 0}
            stats_by_date[target][group_key]['total'] += 1
            if status == 'GREEN':
                stats_by_date[target][group_key]['green'] += 1

    # Formatar para o context
    scanner_assertividade = []
    ordered_keys = ['Geral'] + sorted([k for k in stats_by_date.keys() if k != 'Geral'], reverse=True)

    for day in ordered_keys:
        day_stats = []
        for cat, data in stats_by_date[day].items():
            rate = int((data['green'] / data['total']) * 100) if data['total'] > 0 else 0
            day_stats.append({
                'name': cat,
                'green': data['green'],
                'total': data['total'],
                'rate': rate
            })
        # Ordenar por volume de tips
        day_stats.sort(key=lambda x: -x['total'])
        
        if day_stats:
            scanner_assertividade.append({
                'date_group': day,
                'stats': day_stats
            })

    # Sort: date first, then by probability desc
    sort_func = lambda x: (x['sort_date'] if x['sort_date'] else now_br, -x['prob'])
    for lst in [tips_goals, tips_btts, tips_result, tips_specials, tips_corners, tips_cards, tips_shots]:
        lst.sort(key=sort_func)

    # Split corners and cards categories for side-by-side display
    tips_corners_over = [x for x in tips_corners if x['market'].startswith('CORNERS_OVER_')]
    tips_corners_winner = [x for x in tips_corners if x['market'].startswith('CORNER_WIN_')]
    tips_cards_over = [x for x in tips_cards if x['market'].startswith('CARDS_OVER_')]
    tips_cards_winner = [x for x in tips_cards if x['market'].startswith('CARD_WIN_')]

    # Legacy compat: keep old variable names for the existing template cards
    high_ht_goals = [x for x in tips_goals if x['market'] == 'HT_GOAL']
    high_over15 = [x for x in tips_goals if x['market'] == 'OVER_15']
    high_over25 = [x for x in tips_goals if x['market'] == 'OVER_25']
    high_btts = tips_btts
    high_win = [x for x in tips_result if x['market'] in ('HOME_WIN', 'AWAY_WIN')]
    first_to_score = [x for x in tips_result if x['market'] in ('FIRST_SCORE_HOME', 'FIRST_SCORE_AWAY')]
    high_corners = [x for x in tips_corners if x['market'] == 'CORNERS_OVER_95']
    
    # Enrich legacy items with expected keys
    for item in high_ht_goals: item['ht_goal'] = item['prob']
    for item in high_over15: item['over_15'] = item['prob']
    for item in high_over25: item['over_25'] = item['prob']
    for item in high_btts: item['btts'] = item['prob']
    for item in high_win: item['team_to_win'] = item['match'].home_team.name if item['market'] == 'HOME_WIN' else item['match'].away_team.name
    for item in first_to_score: item['team_first'] = item['match'].home_team.name if item['market'] == 'FIRST_SCORE_HOME' else item['market'] == 'FIRST_SCORE_AWAY'

    # Calcular Estatísticas do Histórico de Bilhetes (Assertividade)
    all_resolved_tickets = BetTicket.objects.filter(status__in=['Green', 'Red'])
    db_greens = all_resolved_tickets.filter(status='Green').count()
    db_reds = all_resolved_tickets.filter(status='Red').count()

    # Base consolidada histórica real
    historical_greens = 48
    historical_reds = 9

    total_greens = historical_greens + db_greens
    total_reds = historical_reds + db_reds
    total_tickets = total_greens + total_reds
    win_rate = int((total_greens / total_tickets * 100)) if total_tickets > 0 else 0

    total_opps = sum(len(lst) for lst in [tips_goals, tips_btts, tips_result, tips_specials, tips_corners, tips_cards, tips_shots, tips_dc_over, tips_dc_btts])

    context = {
        'is_premium': True,
        # Legacy
        'high_ht_goals': high_ht_goals,
        'high_over15': high_over15,
        'high_over25': high_over25,
        'high_btts': high_btts,
        'high_win': high_win,
        'first_to_score': first_to_score,
        'high_corners': high_corners,
        # New expanded categories
        'tips_goals': tips_goals,
        'tips_btts': tips_btts,
        'tips_result': tips_result,
        'tips_specials': tips_specials,
        'tips_corners': tips_corners,
        'tips_corners_over': tips_corners_over,
        'tips_corners_winner': tips_corners_winner,
        'tips_cards': tips_cards,
        'tips_cards_over': tips_cards_over,
        'tips_cards_winner': tips_cards_winner,
        'tips_shots': tips_shots,
        'tips_dc_over': tips_dc_over,
        'tips_dc_btts': tips_dc_btts,
        # Stats
        'stats_total_tickets': total_tickets,
        'stats_greens': total_greens,
        'stats_reds': total_reds,
        'stats_win_rate': win_rate,
        # Others
        'active_tickets': active_tickets,
        'doubles_tickets': [t for t in active_tickets if t.ticket_type == 'Double'],
        'triples_tickets': [t for t in active_tickets if t.ticket_type == 'Treble'],
        'multiples_tickets': [t for t in active_tickets if t.ticket_type == 'Multiple_4_5'],
        'supers_tickets': [t for t in active_tickets if t.ticket_type == 'Super_6_8'],
        'hedge_tickets': [t for t in active_tickets if t.ticket_type == 'Hedge_Favorito'],
        'trixie_tickets': [t for t in active_tickets if t.ticket_type == 'Trixie'],
        'trixie_dc_tickets': [t for t in active_tickets if t.ticket_type == 'Trixie' and t.strategy == 'DC_GOALS'],
        'trixie_goals_btts_tickets': [t for t in active_tickets if t.ticket_type == 'Trixie' and t.strategy == 'GOALS_BTTS'],
        'trixie_half_goals_tickets': [t for t in active_tickets if t.ticket_type == 'Trixie' and t.strategy == 'HALF_GOALS'],
        'trixie_team_half_tickets': [t for t in active_tickets if t.ticket_type == 'Trixie' and t.strategy == 'TEAM_HALF'],
        'history_tickets': history_tickets,
        'history_groups': history_groups,
        'history_stats_by_market': history_stats_by_market,
        'scanner_assertividade': scanner_assertividade,
        'total_scanned': len(matches),
        'total_opportunities': total_opps,
    }
    return render(request, 'members/premium_dashboard.html', context)


@never_cache
def paywall_view(request):
    """Página que mostra os planos para quem não é premium."""
    return render(request, 'members/paywall.html')
