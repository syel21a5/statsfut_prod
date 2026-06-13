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


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@never_cache
def logout_view(request):
    """Logout seguro compatível com GET e POST, imune a erros de CSRF e cache do Cloudflare."""
    # Salvar a engine de sessão antes de destruir
    session_key = request.session.session_key
    
    # Destruir sessão e deslogar
    logout(request)
    
    # Forçar flush da sessão para garantir que não sobreviva no banco
    if session_key:
        from django.contrib.sessions.backends.db import SessionStore
        try:
            s = SessionStore(session_key=session_key)
            s.delete()
        except Exception:
            pass
    
    messages.info(request, _('You have been logged out.'))
    response = redirect('matches:home')
    
    # Headers anti-cache: forçar o Cloudflare/browser a buscar a versão fresca
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    # Deletar cookies de sessão explicitamente
    response.delete_cookie('sessionid')
    response.delete_cookie('csrftoken')
    
    return response


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
    is_vip = False
    if request.user.is_superuser or request.user.is_staff:
        is_premium = True
        is_vip = True
    elif hasattr(request.user, 'profile'):
        is_premium = request.user.profile.is_premium_active
        is_vip = is_premium and (request.user.profile.plan_type == 'vip')

    br_tz = ZoneInfo('America/Sao_Paulo')
    now_br = timezone.now().astimezone(br_tz)
    start_of_day = now_br.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_of_day + timedelta(days=7) # Próximos 7 dias (Hoje + Amanhã + Próxima Rodada)
    
    matches = Match.objects.filter(
        date__range=(start_of_day, end_date),
        status__in=['NS', 'Not Started', 'Scheduled', 'TBD', 'POSTPONED', 'Postponed'] # Apenas jogos não iniciados
    ).select_related('league', 'home_team', 'away_team').order_by('date')[:150]
    
    # Se não for premium, manda apenas os jogos crus para gerar a tela "borrada" de marketing
    if not is_premium:
        context = {
            'is_premium': False,
            'upcoming_matches': matches[:15],
        }
        return render(request, 'members/premium_dashboard.html', context)

    # Cache interno do Dashboard Premium foi removido a pedido do usuário

    # >> NOVO RADAR AO VIVO <<
    from matches.services.live_radar import LiveRadarService
    live_matches_qs = Match.objects.filter(
        status__in=['Live', 'Halftime', '1H', '2H', 'HT', 'ET', 'P', 'In Play', 'IN_PLAY', 'PAUSED']
    ).select_related('league', 'home_team', 'away_team')
    
    live_radar_matches = []
    for match in live_matches_qs:
        live_radar_matches.append({
            'match': match,
            'pressure': LiveRadarService.calculate_pressure(match, window_minutes=5)
        })

    # Caching check removido

    # ----------------- ROBÔ DE AVALIAÇÃO EM TEMPO REAL -----------------
    from matches.models import ScannerTip, Goal
    
    from django.core.cache import cache
    # Para evitar que a página demore a carregar, rodamos essa avaliação pesada no máximo a cada 3 minutos.
    finished_statuses = ['FT', 'Finished', 'AET', 'PEN', 'Match Finished']
    if not cache.get('premium_dashboard_eval_lock'):
        cache.set('premium_dashboard_eval_lock', 'locked', 180)
        # 1. Avaliar Dicas do Scanner Inteligente
        #    Inclui PENDING (normal) + GREEN/RED recentes (re-avaliação caso placar mude)
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
            
                if sel.status == 'Void':
                    continue
                if sel.status in ['Green', 'Red']:
                    if sel.status == 'Red':
                        any_red = True
                    continue

                is_postponed = m.status in ['POSTPONED', 'Postponed', 'CANCELLED', 'Cancelled', 'SUSPENDED', 'Suspended', 'TBD']
                is_stale = False
                if m.date and m.status not in ['FT', 'Finished', 'Concluded']:
                    is_stale = (timezone.now() - m.date).total_seconds() > (36 * 3600)

                if is_postponed or is_stale:
                    if sel.status != 'Void':
                        sel.status = 'Void'
                        sel.save(update_fields=['status'])
                    continue

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
                elif sel.prediction_market == 'dc_1x_2_4':
                    result = 'Green' if (home_score >= away_score) and (2 <= total_goals <= 4) else 'Red'
                elif sel.prediction_market == 'dc_x2_2_4':
                    result = 'Green' if (away_score >= home_score) and (2 <= total_goals <= 4) else 'Red'
                elif sel.prediction_market == 'over_25_yes':
                    result = 'Green' if (total_goals >= 3) and (home_score > 0 and away_score > 0) else 'Red'
                elif sel.prediction_market == 'under_25_no':
                    result = 'Green' if (total_goals <= 2) and (not (home_score > 0 and away_score > 0)) else 'Red'
                elif sel.prediction_market == 'most_goals_2t':
                    goals_1t = ht_goals
                    goals_2t = total_goals - ht_goals
                    result = 'Green' if goals_2t > goals_1t else 'Red'
                elif sel.prediction_market == 'home_score_2t':
                    home_2t = home_score - ht_home
                    result = 'Green' if home_2t > 0 else 'Red'
                elif sel.prediction_market == 'away_score_2t':
                    away_2t = away_score - ht_away
                    result = 'Green' if away_2t > 0 else 'Red'
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
        status='Pending',
        date_target__gte=start_of_day.date()
    ).prefetch_related('selections__match__home_team', 'selections__match__away_team', 'selections__match__league').order_by('-ticket_type', '-created_at')
    
    history_tickets = BetTicket.objects.filter(
        status__in=['Green', 'Red']
    ).prefetch_related('selections__match__home_team', 'selections__match__away_team', 'selections__match__league').order_by('-ticket_type', '-created_at')[:10]

    # Buscar dicas pendentes para os próximos 7 dias, priorizando alta probabilidade
    # EXCLUIR jogos que começaram há mais de 2.5 horas (pois já acabaram, mesmo que o placar ainda não tenha atualizado no banco)
    cutoff_time = timezone.now() - timedelta(hours=2, minutes=30)
    pending_tips = ScannerTip.objects.filter(
        status='PENDING',
        match__date__range=(cutoff_time, end_date + timedelta(days=1))
    ).select_related('match', 'match__league', 'match__home_team', 'match__away_team').order_by('-probability', 'match__date')
    
    # Buscar histórico de dicas dos últimos 15 dias (GREEN, RED, e PENDING de jogos finalizados)
    fifteen_days_ago = timezone.now() - timedelta(days=15)
    evaluated_tips = ScannerTip.objects.filter(
        status__in=['GREEN', 'RED'],
        match__date__gte=fifteen_days_ago
    ).select_related('match', 'match__league', 'match__home_team', 'match__away_team').order_by('-match__date')
    
    # Incluir PENDING de jogos já finalizados (para que não desapareçam do histórico)
    pending_finished_tips = ScannerTip.objects.filter(
        status='PENDING',
        match__status__in=finished_statuses,
        match__date__gte=fifteen_days_ago
    ).select_related('match', 'match__league', 'match__home_team', 'match__away_team').order_by('-match__date')
    
    # Combinar as duas querysets
    from itertools import chain
    all_history_tips = list(chain(evaluated_tips, pending_finished_tips))

    # Mapeamento de mercados para categorias
    GOALS_MARKETS = {'HT_GOAL', 'OVER_05', 'OVER_15', 'OVER_25', 'OVER_35', 'UNDER_35', 'UNDER_45', 'UNDER_55', 'UNDER_65', 'HT_GOALS_NOT_2_4', 'SH_GOALS_NOT_2_4'}
    BTTS_MARKETS = {'BTTS', 'BTTS_1H', 'BTTS_2H', 'BTTS_BOTH'}
    RESULT_MARKETS = {'HOME_WIN', 'AWAY_WIN', 'DC_1X', 'DC_X2', 'DNB_HOME', 'DNB_AWAY', 'FIRST_SCORE_HOME', 'FIRST_SCORE_AWAY', 'HT_HOME_WIN', 'HT_AWAY_WIN'}
    SPECIALS_MARKETS = {'HOME_CS', 'AWAY_CS', 'HOME_WTN', 'AWAY_WTN', 'HC_HOME_M05', 'HC_HOME_M15', 'HC_AWAY_P15', 'MARGIN_H1', 'MARGIN_H2', 'WIN_BTTS_HY', 'WIN_BTTS_AY', 'WIN_BTTS_HN', 'MOST_1H', 'MOST_2H'}
    CORNERS_MARKETS = {'CORNERS_OVER_65', 'CORNERS_OVER_75', 'CORNERS_OVER_85', 'CORNERS_OVER_95', 'CORNERS_OVER_105', 'CORNERS_OVER_115', 'CORNER_WIN_H', 'CORNER_WIN_A'}
    CARDS_MARKETS = {'CARDS_OVER_35', 'CARDS_OVER_45', 'CARDS_OVER_55', 'CARDS_OVER_65', 'CARD_WIN_H', 'CARD_WIN_A'}
    SHOTS_MARKETS = {'SHOTS_OVER_205', 'SHOTS_OVER_225', 'SHOTS_OVER_245', 'SOT_OVER_65', 'SOT_OVER_75', 'SOT_OVER_85', 'SHOT_WIN_H', 'SHOT_WIN_A'}
    
    def get_date_group(match_date):
        if not match_date: return _("Future")
        match_date_br = match_date.astimezone(br_tz).date()
        today = now_br.date()
        diff = (match_date_br - today).days
        if diff == 0: return _("Today")
        elif diff == 1: return _("Tomorrow")
        return _("Next Round")

    def get_ticket_date_group(target_date):
        if not target_date: return _("Future")
        today = now_br.date()
        diff = (target_date - today).days
        if diff == 0: return _("Today")
        elif diff == 1: return _("Tomorrow")
        return _("Next Round")

    for t in active_tickets:
        if t.date_target:
            t.date_group = get_ticket_date_group(t.date_target)
        else:
            first_sel = t.selections.first()
            if first_sel and first_sel.match.date:
                t.date_group = get_date_group(first_sel.match.date)
            else:
                t.date_group = _("Future")

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
            return _("Home or Draw & Under %(line)s Goals") % {'line': line}
        elif m.startswith('DC_X2_UNDER_'):
            line = m.replace('DC_X2_UNDER_', '').replace('_', '.')
            return _("Draw or Away & Under %(line)s Goals") % {'line': line}
        elif m.startswith('DC_1X_OVER_'):
            line = m.replace('DC_1X_OVER_', '').replace('_', '.')
            return _("Home or Draw & Over %(line)s Goals") % {'line': line}
        elif m.startswith('DC_X2_OVER_'):
            line = m.replace('DC_X2_OVER_', '').replace('_', '.')
            return _("Draw or Away & Over %(line)s Goals") % {'line': line}
        elif m == 'DC_1X_BTTS_YES':
            return _("Home or Draw & BTTS Yes")
        elif m == 'DC_1X_BTTS_NO':
            return _("Home or Draw & BTTS No")
        elif m == 'DC_X2_BTTS_YES':
            return _("Draw or Away & BTTS Yes")
        elif m == 'DC_X2_BTTS_NO':
            return _("Draw or Away & BTTS No")
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
        elif m == 'CORNERS_OVER_65': return _("Over 6.5 Corners")
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
        is_live = tip.match.status in ['Live', 'Halftime', '1H', '2H', 'HT', 'ET', 'P', 'In Play', 'IN_PLAY', 'PAUSED']
        item = {
            'match': tip.match,
            'prob': tip.probability,
            'odd': tip.odd,
            'text': get_translated_text(tip),
            'market': tip.market,
            'date_group': get_date_group(tip.match.date),
            'sort_date': tip.match.date,
            'is_live': is_live,
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

    def get_date_group_order(match_date):
        if not match_date: return 99
        match_date_br = match_date.astimezone(br_tz).date()
        today = now_br.date()
        diff = (match_date_br - today).days
        if diff == 0: return 0
        elif diff == 1: return 1
        return 2



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

    # Ordenar por maior probabilidade geral primeiro
    prob_sort_func = lambda x: (-x['prob'], x['sort_date'] if x['sort_date'] else now_br)
    for lst in [tips_goals, tips_btts, tips_result, tips_specials, tips_corners, tips_cards, tips_shots, tips_dc_over, tips_dc_btts]:
        lst.sort(key=prob_sort_func)

    MAX_TIPS_PER_MARKET_PER_DATE = 30  # Top 30 melhores por DIA e por MERCADO (ex: 30 pro Over 0.5 hoje, 30 pro Over 1.5 hoje...)

    def limit_per_market_and_date(lst, limit):
        counts = {}
        filtered = []
        for x in lst:
            # A chave única é o (grupo_da_data, mercado)
            g = (get_date_group_order(x['sort_date']), x['market'])
            counts[g] = counts.get(g, 0) + 1
            if counts[g] <= limit:
                filtered.append(x)
        
        # Re-agrupar na ordem de data (0, 1, 2) para o template
        filtered.sort(key=lambda x: (get_date_group_order(x['sort_date']), -x['prob']))
        return filtered

    # Limitar a top X por dia E por mercado, garantindo abas fartas
    tips_goals = limit_per_market_and_date(tips_goals, MAX_TIPS_PER_MARKET_PER_DATE)
    tips_btts = limit_per_market_and_date(tips_btts, MAX_TIPS_PER_MARKET_PER_DATE)
    tips_result = limit_per_market_and_date(tips_result, MAX_TIPS_PER_MARKET_PER_DATE)
    tips_specials = limit_per_market_and_date(tips_specials, MAX_TIPS_PER_MARKET_PER_DATE)
    tips_corners = limit_per_market_and_date(tips_corners, MAX_TIPS_PER_MARKET_PER_DATE)
    tips_cards = limit_per_market_and_date(tips_cards, MAX_TIPS_PER_MARKET_PER_DATE)
    tips_shots = limit_per_market_and_date(tips_shots, MAX_TIPS_PER_MARKET_PER_DATE)
    tips_dc_over = limit_per_market_and_date(tips_dc_over, MAX_TIPS_PER_MARKET_PER_DATE)
    tips_dc_btts = limit_per_market_and_date(tips_dc_btts, MAX_TIPS_PER_MARKET_PER_DATE)

    # Split corners and cards categories for side-by-side display
    tips_corners_over = [x for x in tips_corners if x['market'].startswith('CORNERS_OVER_')]
    tips_corners_winner = [x for x in tips_corners if x['market'].startswith('CORNER_WIN_')]
    tips_cards_over = [x for x in tips_cards if x['market'].startswith('CARDS_OVER_')]
    tips_cards_winner = [x for x in tips_cards if x['market'].startswith('CARD_WIN_')]
    tips_shots_total = [x for x in tips_shots if x['market'].startswith('SHOTS_OVER_') or x['market'].startswith('SHOT_WIN_')]
    tips_shots_target = [x for x in tips_shots if x['market'].startswith('SOT_OVER_')]

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
        'is_vip': is_vip,
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
        'tips_shots_total': tips_shots_total,
        'tips_shots_target': tips_shots_target,
        'tips_dc_over': tips_dc_over,
        'tips_dc_btts': tips_dc_btts,
        # Stats
        'stats_total_tickets': total_tickets,
        'stats_greens': total_greens,
        'stats_reds': total_reds,
        'stats_win_rate': win_rate,
        # Others
        'live_radar_matches': live_radar_matches,
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


import json
import logging
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from members.models import UserProfile
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@csrf_exempt
def kiwify_webhook(request):
    """
    Webhook da Kiwify para ativação automática de planos premium.
    Segurança: verificar query param ?secret=TOKEN
    """
    secret_token = request.GET.get('secret')
    EXPECTED_SECRET = getattr(settings, 'KIWIFY_WEBHOOK_SECRET', 'statsfut_kiwify_key_2026')
    if secret_token != EXPECTED_SECRET:
        return HttpResponse("Unauthorized", status=401)

    if request.method != 'POST':
        return HttpResponse("Method Not Allowed", status=405)

    try:
        data = json.loads(request.body)
        order_status = data.get('order_status')
        customer = data.get('Customer', {}) or {}
        email = customer.get('email')
        product_name = data.get('product_name', '').lower()
        
        if not email:
            return JsonResponse({'status': 'ignored', 'message': 'No customer email'}, status=400)

        plan_type = 'popular'
        if 'vip' in product_name or 'best' in product_name:
            plan_type = 'vip'

        days = 30
        plan_info = data.get('plan', {}) or {}
        frequency = plan_info.get('frequency', 'mensal').lower()
        if 'tri' in frequency or '3' in frequency or 'quarter' in frequency:
            days = 90

        if order_status in ['paid', 'approved', 'subscription_renewed']:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0] + '_sf',
                    'is_active': True
                }
            )
            if created:
                user.set_password(User.objects.make_random_password())
                user.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.is_premium = True
            profile.plan_type = plan_type
            profile.premium_until = timezone.now() + timedelta(days=days)
            profile.save()

            logger.info(f"Kiwify webhook: Activated {plan_type} premium for user {email} until {profile.premium_until}")
            return JsonResponse({'status': 'success', 'message': 'Premium activated'})

        elif order_status in ['refunded', 'canceled', 'chargeback']:
            try:
                user = User.objects.get(email=email)
                profile = user.profile
                profile.is_premium = False
                profile.save()
                logger.info(f"Kiwify: Deactivated premium for user {email}")
                return JsonResponse({'status': 'success', 'message': 'Premium deactivated'})
            except User.DoesNotExist:
                return JsonResponse({'status': 'ignored', 'message': 'User not found'})

        return JsonResponse({'status': 'ignored', 'message': f'Status {order_status} ignored'})

    except Exception as e:
        logger.error(f"Error in Kiwify webhook: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
def stripe_webhook(request):
    """
    Webhook da Stripe para ativação automática de planos premium.
    Segurança: verificar query param ?secret=TOKEN
    """
    secret_token = request.GET.get('secret')
    EXPECTED_SECRET = getattr(settings, 'STRIPE_WEBHOOK_SECRET', 'statsfut_stripe_key_2026')
    if secret_token != EXPECTED_SECRET:
        return HttpResponse("Unauthorized", status=401)

    if request.method != 'POST':
        return HttpResponse("Method Not Allowed", status=405)

    try:
        data = json.loads(request.body)
        event_type = data.get('type')

        if event_type == 'checkout.session.completed':
            session = data.get('data', {}).get('object', {})
            email = session.get('customer_details', {}).get('email')
            if not email:
                email = session.get('customer_email')

            if not email:
                return JsonResponse({'status': 'ignored', 'message': 'No customer email'}, status=400)

            plan_type = 'popular'
            description = session.get('description', '') or ''
            description = description.lower()
            if 'vip' in description or 'best' in description:
                plan_type = 'vip'

            days = 30
            if 'tri' in description or '3' in description or 'quarter' in description:
                days = 90

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0] + '_sf',
                    'is_active': True
                }
            )
            if created:
                user.set_password(User.objects.make_random_password())
                user.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.is_premium = True
            profile.plan_type = plan_type
            profile.premium_until = timezone.now() + timedelta(days=days)
            profile.save()

            logger.info(f"Stripe: Activated {plan_type} premium for {email}")
            return JsonResponse({'status': 'success', 'message': 'Premium activated'})

        elif event_type in ['customer.subscription.deleted', 'invoice.payment_failed']:
            subscription = data.get('data', {}).get('object', {})
            email = subscription.get('customer_email')
            if email:
                try:
                    user = User.objects.get(email=email)
                    profile = user.profile
                    profile.is_premium = False
                    profile.save()
                    logger.info(f"Stripe: Deactivated premium for {email}")
                    return JsonResponse({'status': 'success', 'message': 'Premium deactivated'})
                except User.DoesNotExist:
                    pass

        return JsonResponse({'status': 'ignored', 'message': f'Event {event_type} ignored'})

    except Exception as e:
        logger.error(f"Error in Stripe webhook: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

