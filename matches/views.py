from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Match, League, Team, Season, LeagueStanding
from django.db import models

from .api_manager import APIManager
import json


class MatchDetailView(DetailView):
    model = Match
    template_name = 'matches/match_detail.html'
    context_object_name = 'match'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = self.object
        
        # Se não tem predictions e o jogo não é passado (ou é recente?), busca na API
        if not match.predictions_data:
            # So busca se tiver api_id (salvo pelo scraper)
            if match.api_id:
                print(f"Fetching predictions for match API_ID {match.api_id}...")
                api_manager = APIManager()
                
                try:
                    preds = api_manager.get_predictions(match.api_id)
                    if preds:
                        match.predictions_data = preds[0] # API retorna lista
                        match.save()
                except Exception as e:
                    print(f"Erro ao atualizar predictions: {e}")
            else:
                 print(f"Match {match.id} sem API_ID. Ignorando fetch de predictions.")
        
        return context

class HomeView(ListView):

    model = Match
    template_name = 'matches/home.html'
    context_object_name = 'matches'
    
    def get_queryset(self):
        filter_type = self.request.GET.get('filter', 'today')
        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if filter_type == 'tomorrow':
            start_date = start_of_day + timedelta(days=1)
            end_date = start_date + timedelta(days=1)
            return Match.objects.filter(date__range=(start_date, end_date)).order_by('date')
            
        elif filter_type == 'next_round':
            # Próximos 14 dias para garantir
            start_date = start_of_day + timedelta(days=2)
            end_date = start_date + timedelta(days=14)
            return Match.objects.filter(date__range=(start_date, end_date)).order_by('date')
            
        else: # today
            end_date = start_of_day + timedelta(days=1)
            return Match.objects.filter(date__range=(start_of_day, end_date)).order_by('status', 'date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_type = self.request.GET.get('filter', 'today')
        context['current_filter'] = filter_type
        
        if filter_type == 'tomorrow':
            context['page_title'] = "Tomorrow's Matches"
        elif filter_type == 'next_round':
            context['page_title'] = 'Next Round'
        else:
            context['page_title'] = "Today\'s Matches"
            
        return context

class LiveMatchesView(ListView):
    model = Match
    template_name = 'matches/live_matches.html'
    context_object_name = 'matches'
    
    def get_queryset(self):
        # Todos os status que indicam jogo ao vivo
        live_statuses = [
            '1H', '2H', 'HT', 'ET', 'P', 'BT', 'LIVE', 'IN_PLAY', 'PAUSED', 
            'INT', 'SUSP', 'BREAK', 'PEN_LIVE'
        ]
        return Match.objects.filter(status__in=live_statuses).select_related('league', 'home_team', 'away_team').order_by('league__name', 'date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        matches = context['matches']
        
        # Agrupar por Liga
        grouped_matches = {}
        for match in matches:
            league_name = match.league.name
            if league_name not in grouped_matches:
                grouped_matches[league_name] = {'league': match.league, 'matches': []}
            grouped_matches[league_name]['matches'].append(match)
            
        context['grouped_matches'] = grouped_matches
        context['page_title'] = 'Live Matches'
        return context

class LeagueDetailView(DetailView):
    model = League
    template_name = 'matches/league_dashboard.html'
    context_object_name = 'league'
    
    def get_object(self):
        # Se pk foi passado, usa comportamento padrão
        if 'pk' in self.kwargs:
            return super().get_object()
            
        # Busca por nome (slug)
        league_slug = self.kwargs.get('league_name')
        if league_slug:
            name_query = league_slug.replace('-', ' ')
            # Tenta busca exata (insensível a maiúsculas)
            league = League.objects.filter(name__iexact=name_query).first()
            if not league:
                 # Tenta contem
                 league = League.objects.filter(name__icontains=name_query).first()
            
            if league:
                return league
                
        # Fallback (não deve acontecer se configurado certo)
        from django.http import Http404
        raise Http404("League not found")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        league = self.object
        now = timezone.now()
        
        context['upcoming_matches'] = Match.objects.filter(
            league=league,
            date__gte=now,
            status__in=['Scheduled', 'Not Started']
        ).order_by('date')[:15]
        
        context['latest_results'] = Match.objects.filter(
            league=league,
            status='Finished',
            date__lte=now
        ).order_by('-date')[:15]
        
        latest_season = league.standings.order_by('-season__year').first().season if league.standings.exists() else None
        context['latest_season'] = latest_season
        
        if latest_season:
            # Fetch all necessary data in bulk to avoid N+1 queries
            standings = list(league.standings.filter(season=latest_season).order_by('position'))
            all_matches = Match.objects.filter(
                league=league,
                season=latest_season,
                status='Finished',
                # date__lt=today # REMOVED: Allow test data with NULL dates
            ).select_related('home_team', 'away_team')

            # Initialize data structures for Home/Away tables
            team_stats = {} # Key: team_id, Value: {home_stats, away_stats}

            # Pre-calculate PPG for all teams for Relative Performance calculation
            team_ppg_map = {}
            for s in standings:
                if s.played > 0:
                    team_ppg_map[s.team.id] = s.points / s.played
                else:
                    team_ppg_map[s.team.id] = 0.0

            for standing in standings:
                team_id = standing.team.id
                team_stats[team_id] = {
                   'team': standing.team,
                   'team_slug': standing.team.name.replace(' ', '-'),
                   'league_slug': league.name.replace(' ', '-'),
                   'home': {'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0},
                   'away': {'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0},
                   'form': [] 
                }
                # Calculate Goal Diff for main table
                standing.goal_diff = standing.goals_for - standing.goals_against
                
                # --- NEW: Slugify names for custom URLs ---
                standing.team_slug = standing.team.name.replace(' ', '-')
                standing.league_slug = league.name.replace(' ', '-') # Assuming league object is available

                # Calculate Form (Last 5 for main table, Last 8 for Form tab)
                team_matches = [m for m in all_matches if m.home_team_id == team_id or m.away_team_id == team_id]
                # Sort by date/id descending
                team_matches.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                
                # Last 5 for Main Table
                # --- NEW: POPULATE TEAM STATS (Home/Away Tables) ---
                t_stats = team_stats[team_id]
                for m in team_matches:
                    if m.home_team_id == team_id:
                        s = t_stats['home']
                        s['gp'] += 1
                        s['gf'] += m.home_score
                        s['ga'] += m.away_score
                        if m.home_score > m.away_score: s['w'] += 1; s['pts'] += 3
                        elif m.home_score == m.away_score: s['d'] += 1; s['pts'] += 1
                        else: s['l'] += 1
                    else:
                        s = t_stats['away']
                        s['gp'] += 1
                        s['gf'] += m.away_score
                        s['ga'] += m.home_score
                        if m.away_score > m.home_score: s['w'] += 1; s['pts'] += 3
                        elif m.away_score == m.home_score: s['d'] += 1; s['pts'] += 1
                        else: s['l'] += 1

                form_5 = []
                form_details = []  # NEW: Detailed info for tooltips
                for m in team_matches[:5]:
                    # Determine if team was home or away
                    is_home = m.home_team_id == team_id
                    opponent = m.away_team if is_home else m.home_team
                    team_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    
                    # Determine result
                    if team_score > opp_score:
                        result = 'W'
                    elif team_score == opp_score:
                        result = 'D'
                    else:
                        result = 'L'
                    
                    form_5.append(result)
                    
                    # Add detailed info
                    form_details.append({
                        'date': m.date.strftime('%d %b') if m.date else '-',
                        'opponent': opponent.name,
                        'score': f"{team_score}-{opp_score}",
                        'result': result,
                        'is_home': is_home
                    })
                
                standing.form_history = form_5
                standing.form_details = form_details  # NEW

                # Last 8 for Relative Form Tab
                form_8 = []
                pts_8 = 0
                for m in team_matches[:8]:
                    result = ''
                    if m.home_team_id == team_id:
                        if m.home_score > m.away_score: result = 'W'; pts_8 += 3
                        elif m.home_score == m.away_score: result = 'D'; pts_8 += 1
                        else: result = 'L'
                    else:
                        if m.away_score > m.home_score: result = 'W'; pts_8 += 3
                        elif m.away_score == m.home_score: result = 'D'; pts_8 += 1
                        else: result = 'L'
                    form_8.append(result)
                
                standing.form_8 = form_8
                standing.pts_8 = pts_8
                standing.ppg_8 = round(pts_8 / 8, 2) if len(team_matches) >= 8 else round(pts_8 / len(team_matches), 2) if team_matches else 0
                standing.ppg_season = round(standing.points / standing.played, 2) if standing.played > 0 else 0
                standing.ppg_diff = round(standing.ppg_8 - standing.ppg_season, 2)
                
                # Relative Form Percentage ((PPG8 - PPG_Season) / PPG_Season)
                if standing.ppg_season > 0:
                    standing.relative_form_pct = round(((standing.ppg_8 - standing.ppg_season) / standing.ppg_season) * 100, 0)
                    standing.relative_form_pct = int(standing.relative_form_pct)
                    # Bar width: 1% = 1.5px approx? Or just pass absolute value for flexible JS/CSS use.
                    # Let's pass a calc valid for 'px' usage.
                    # Using factor 2.0: 10% = 20px. 40% = 80px. 90% = 180px.
                    # Maybe cap at 100px?
                    standing.relative_form_bar_width = min(abs(standing.relative_form_pct) * 2, 120) 
                else:
                    standing.relative_form_pct = 0
                    standing.relative_form_bar_width = 0
                
                # Relative Performance metrics (SoccerStats style)
                # Points Performance Index = Team PPG x Opponents PPG
                
                opponents_ppg_sum = 0
                opponents_count = 0
                
                for m in team_matches:
                    opp_id = m.away_team_id if m.home_team_id == team_id else m.home_team_id
                    if opp_id in team_ppg_map:
                        opponents_ppg_sum += team_ppg_map[opp_id]
                        opponents_count += 1
                
                standing.opponents_ppg = round(opponents_ppg_sum / opponents_count, 2) if opponents_count > 0 else 0
                standing.performance_index = round(standing.ppg_season * standing.opponents_ppg, 2)
                # Calulca a porcentagem para a barra (máximo 4.0 = 100%)
                standing.perf_width_pct = min(round((standing.performance_index / 4.0) * 100, 1), 100) if standing.performance_index > 0 else 0

                # --- Run-in Analysis Logic ---
                # Get all matches for this team (including scheduled)
                team_all_matches = Match.objects.filter(
                    league=league,
                ).filter(models.Q(home_team_id=team_id) | models.Q(away_team_id=team_id)).select_related('home_team', 'away_team')

                played_opp_ppg_sum = 0
                played_count = 0
                remaining_opp_ppg_sum = 0
                remaining_count = 0
                
                # Sort upcoming by date/id
                upcoming_scheduled = []
                
                for m in team_all_matches:
                    opp_id = m.away_team_id if m.home_team_id == team_id else m.home_team_id
                    opp_ppg = team_ppg_map.get(opp_id, 0.0)
                    
                    if m.status == 'Finished':
                        played_opp_ppg_sum += opp_ppg
                        played_count += 1
                    elif m.status == 'Scheduled':
                        remaining_opp_ppg_sum += opp_ppg
                        remaining_count += 1
                        upcoming_scheduled.append({'match': m, 'opp_ppg': opp_ppg})

                # Opponents Played PPG
                standing.opp_played_ppg = round(played_opp_ppg_sum / played_count, 2) if played_count > 0 else 0
                
                # Opponents Remaining PPG
                standing.opp_remaining_ppg = round(remaining_opp_ppg_sum / remaining_count, 2) if remaining_count > 0 else 0
                standing.runin_width_pct = min(round((standing.opp_remaining_ppg / 3.0) * 100, 1), 100) if standing.opp_remaining_ppg > 0 else 0
                
                # Played vs Remaining (%)
                if standing.opp_remaining_ppg > 0:
                    diff_pct = (standing.opp_played_ppg / standing.opp_remaining_ppg - 1) * 100
                    standing.runin_diff_pct = round(diff_pct, 1)
                else:
                    standing.runin_diff_pct = 0
                
                # Next 4 Opponents average
                upcoming_scheduled.sort(key=lambda x: (x['match'].date if x['match'].date else timezone.now().date(), x['match'].id))
                next_4 = upcoming_scheduled[:4]
                next_4_sum = sum(item['opp_ppg'] for item in next_4)
                standing.next_4_ppg = round(next_4_sum / len(next_4), 2) if next_4 else 0

                # --- Projected Points Logic ---
                # Ratio = Opponents Remaining PPG / Opponents Played PPG
                if standing.opp_played_ppg > 0:
                    standing.proj_ratio = round(standing.opp_remaining_ppg / standing.opp_played_ppg, 2)
                else:
                    standing.proj_ratio = 1.0
                
                # pPPG = Team PPG x Ratio
                standing.proj_ppg = round(standing.ppg_season * standing.proj_ratio, 2)
                
                # Games Remaining
                standing.games_remaining = 38 - standing.played
                
                # Projected Points = pPPG x Games Remaining
                standing.proj_points = round(standing.proj_ppg * standing.games_remaining, 2)
                
                # Projected Total = Current Points + Projected Points
                standing.proj_total = round(standing.points + standing.proj_points, 2)

                # --- Additional Stats for Main Table ---
                # Clean Sheets (CS): matches where GA = 0
                clean_sheets = sum(1 for m in team_matches if (
                    (m.home_team_id == team_id and m.away_score == 0) or
                    (m.away_team_id == team_id and m.home_score == 0)
                ))
                standing.clean_sheets = clean_sheets
                
                # Scoring Rate (SR): percentage of matches where team scored
                matches_scored = sum(1 for m in team_matches if (
                    (m.home_team_id == team_id and m.home_score > 0) or
                    (m.away_team_id == team_id and m.away_score > 0)
                ))
                standing.scoring_rate = f"{round((matches_scored / len(team_matches) * 100) if team_matches else 0)}%"
                
                # Maximum Possible Points (MPP)
                standing.max_possible_points = standing.points + (38 - standing.played) * 3


            # Calculate table averages
            total_teams = len(standings)
            if total_teams > 0:
                context['avg_played'] = sum(s.played for s in standings) / total_teams
                context['avg_won'] = sum(s.won for s in standings) / total_teams
                context['avg_drawn'] = sum(s.drawn for s in standings) / total_teams
                context['avg_lost'] = sum(s.lost for s in standings) / total_teams
                context['avg_gf'] = sum(s.goals_for for s in standings) / total_teams
                context['avg_ga'] = sum(s.goals_against for s in standings) / total_teams
                context['avg_gd'] = sum(s.goal_diff for s in standings) / total_teams
                context['avg_pts'] = sum(s.points for s in standings) / total_teams
                context['avg_ppg'] = sum(s.ppg_season for s in standings) / total_teams
                context['avg_ppg8'] = sum(s.ppg_8 for s in standings) / total_teams
                context['avg_cs'] = sum(s.clean_sheets for s in standings) / total_teams * 100 / context['avg_played'] if context['avg_played'] > 0 else 0
                # SR average: percentage of teams that scored in their matches
                total_sr = sum(int(s.scoring_rate.rstrip('%')) for s in standings)
                context['avg_sr'] = total_sr / total_teams if total_teams > 0 else 0


            # Prepare sorted lists for context
            home_table = []
            away_table = []
            for tid, data in team_stats.items():
                # Add calculated properties
                h = data['home']
                h['team'] = data['team']
                h['team_slug'] = data['team_slug']
                h['league_slug'] = data['league_slug']
                h['gd'] = h['gf'] - h['ga']
                h['ppg'] = round(h['pts'] / h['gp'], 2) if h['gp'] > 0 else 0
                home_table.append(h)

                a = data['away']
                a['team'] = data['team']
                a['team_slug'] = data['team_slug']
                a['league_slug'] = data['league_slug']
                a['gd'] = a['gf'] - a['ga']
                a['ppg'] = round(a['pts'] / a['gp'], 2) if a['gp'] > 0 else 0
                away_table.append(a)

            # Sort tables (Pts desc, GD desc, GF desc)
            home_table.sort(key=lambda x: (x['pts'], x['gd'], x['gf']), reverse=True)
            away_table.sort(key=lambda x: (x['pts'], x['gd'], x['gf']), reverse=True)

            # Add rank
            for i, row in enumerate(home_table, 1): row['position'] = i
            for i, row in enumerate(away_table, 1): row['position'] = i

            context['standings'] = standings
            context['home_table'] = home_table
            context['away_table'] = away_table
            
            # Relative Home/Away Performance Table
            relative_table = []
            for tid, data in team_stats.items():
                row = {}
                row['team'] = data['team']
                row['team_slug'] = data['team_slug']
                row['league_slug'] = data['league_slug']
                row['gph'] = data['home']['gp']
                row['gpa'] = data['away']['gp']
                row['pts'] = data['home']['pts'] + data['away']['pts']
                
                # Calculate PPGs
                ppg_home = round(data['home']['pts'] / data['home']['gp'], 2) if data['home']['gp'] > 0 else 0
                ppg_away = round(data['away']['pts'] / data['away']['gp'], 2) if data['away']['gp'] > 0 else 0
                
                row['ppg_home'] = ppg_home
                row['ppg_away'] = ppg_away
                row['ppg_diff'] = round(ppg_home - ppg_away, 2)
                row['ppg_diff_abs'] = abs(row['ppg_diff'])
                
                # Bar width (max diff usually around 2.0, so scaling to 100px or %)
                # Using 80px as max width base
                row['bar_width'] = min(int(abs(row['ppg_diff']) * 40), 100)
                
                relative_table.append(row)
            
            # Sort by Points (desc), then PPG Difference (desc)
            relative_table.sort(key=lambda x: (x['pts'], x['ppg_diff']), reverse=True)
            
            # Add Rank
            for i, row in enumerate(relative_table, 1): row['position'] = i
            
            context['relative_table'] = relative_table
            
            # Get upcoming matches_qs
            upcoming_matches_qs = Match.objects.filter(
                league=league,
                status__in=['Scheduled', 'Not Started'],
                date__gte=timezone.now()
            ).select_related('home_team', 'away_team').order_by('date')[:100]
            
            # Group upcoming matches and calculate stats for each team
            for standing in standings:
                team_id = standing.team.id
                team_matches = [m for m in upcoming_matches_qs if m.home_team_id == team_id or m.away_team_id == team_id][:5]
                standing.upcoming_matches = team_matches
                standing.empty_slots = range(5 - len(team_matches))
                
                # Projected points (current PPG * remaining games in 38-game season)
                remaining_games = 38 - standing.played
                projected_additional = standing.ppg_season * remaining_games
                standing.projected_total = round(standing.points + projected_additional, 0)
            
            # Prepare Statistics Tab Data (Upcoming Matches)
            stats_entries = []
            for match in upcoming_matches_qs:
                home_id = match.home_team_id
                away_id = match.away_team_id
                
                # Default stats if missing
                default_stats = {'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0}
                
                h_stats = team_stats[home_id]['home'] if home_id in team_stats else default_stats.copy()
                a_stats = team_stats[away_id]['away'] if away_id in team_stats else default_stats.copy()
                
                # PPG % (Base is 3 points)
                h_ppg = h_stats['pts'] / h_stats['gp'] if h_stats['gp'] > 0 else 0
                a_ppg = a_stats['pts'] / a_stats['gp'] if a_stats['gp'] > 0 else 0
                
                # WDL Distribution (Bar widths)
                h_gp = h_stats['gp'] if h_stats['gp'] > 0 else 1
                a_gp = a_stats['gp'] if a_stats['gp'] > 0 else 1
                
                h_w_pct = (h_stats['w'] / h_gp) * 100
                h_d_pct = (h_stats['d'] / h_gp) * 100
                h_l_pct = (h_stats['l'] / h_gp) * 100
                
                a_w_pct = (a_stats['w'] / a_gp) * 100
                a_d_pct = (a_stats['d'] / a_gp) * 100
                a_l_pct = (a_stats['l'] / a_gp) * 100
                
                # Goal Averages
                h_gf_avg = h_stats['gf'] / h_gp
                h_ga_avg = h_stats['ga'] / h_gp
                a_gf_avg = a_stats['gf'] / a_gp
                a_ga_avg = a_stats['ga'] / a_gp
                
                h_tg_avg = h_gf_avg + h_ga_avg
                a_tg_avg = a_gf_avg + a_ga_avg
                
                # Last 4 Form (From form_history, take last 4)
                # Note: form_history in context is Last 5 overall. We need Last 4 Home/Away specifically? 
                # The image says "Last 4" but subtab is "Home/Away". 
                # Assuming Last 4 Home matches for Home team, Last 4 Away matches for Away team.
                # We need to fetch specific form for H/A? view already calculated 'all_matches'.
                
                # Recalculate H/A specific form
                h_matches = [m for m in all_matches if m.home_team_id == home_id]
                h_matches.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                h_form_4 = []
                for m in h_matches[:4]:
                    if m.home_score > m.away_score: h_form_4.append('W')
                    elif m.home_score == m.away_score: h_form_4.append('D')
                    else: h_form_4.append('L')
                    
                a_matches = [m for m in all_matches if m.away_team_id == away_id]
                a_matches.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                a_form_4 = []
                for m in a_matches[:4]:
                    if m.away_score > m.home_score: a_form_4.append('W')
                    elif m.away_score == m.home_score: a_form_4.append('D')
                    else: a_form_4.append('L')
                        
                entry = {
                    'match': match,
                    'home_team': match.home_team,
                    'away_team': match.away_team,
                    'h_ppg_pct': int((h_ppg / 3) * 100),
                    'a_ppg_pct': int((a_ppg / 3) * 100),
                    'h_wdl': {'w': h_w_pct, 'd': h_d_pct, 'l': h_l_pct},
                    'a_wdl': {'w': a_w_pct, 'd': a_d_pct, 'l': a_l_pct},
                    'h_goals': {'gf': round(h_gf_avg, 2), 'ga': round(h_ga_avg, 2), 'tg': round(h_tg_avg, 2)},
                    'a_goals': {'gf': round(a_gf_avg, 2), 'ga': round(a_ga_avg, 2), 'tg': round(a_tg_avg, 2)},
                    'h_over_25': 0, # Placeholder
                    'a_over_25': 0, # Placeholder
                    'h_last_4': h_form_4,
                    'a_last_4': a_form_4
                }
                
                # Calculate Over 2.5 %
                h_over_count = sum(1 for m in h_matches if (m.home_score + m.away_score) > 2.5)
                entry['h_over_25'] = int((h_over_count / len(h_matches) * 100)) if h_matches else 0
                
                a_over_count = sum(1 for m in a_matches if (m.home_score + m.away_score) > 2.5)
                entry['a_over_25'] = int((a_over_count / len(a_matches) * 100)) if a_matches else 0
                
                stats_entries.append(entry)

            # Prepare Statistics Tab Data (Overall)
            stats_entries_overall = []
            
            # Map standings by team_id for easier access
            standings_map = {s.team.id: s for s in standings}
            
            for match in upcoming_matches_qs:
                home_id = match.home_team_id
                away_id = match.away_team_id
                
                # Default standing if missing (should use empty object-like struct)
                # But we can just use 0 values if not found.
                
                h_standing = standings_map.get(home_id)
                a_standing = standings_map.get(away_id)
                
                # Helper to get stats safely
                def get_safe_stats(standing):
                    if not standing:
                        return {'ppg': 0, 'w_pct': 0, 'd_pct': 0, 'l_pct': 0, 'gf_avg': 0, 'ga_avg': 0, 'tg_avg': 0}
                    gp = standing.played if standing.played > 0 else 1
                    return {
                        'ppg': standing.ppg_season,
                        'w_pct': (standing.won / gp) * 100,
                        'd_pct': (standing.drawn / gp) * 100,
                        'l_pct': (standing.lost / gp) * 100,
                        'gf_avg': standing.goals_for / gp,
                        'ga_avg': standing.goals_against / gp,
                        'tg_avg': (standing.goals_for + standing.goals_against) / gp
                    }

                h_s = get_safe_stats(h_standing)
                a_s = get_safe_stats(a_standing)
                
                # Last 4 Form (Overall)
                h_matches_all = [m for m in all_matches if m.home_team_id == home_id or m.away_team_id == home_id]
                h_matches_all.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                h_form_4 = []
                for m in h_matches_all[:4]:
                    is_home = m.home_team_id == home_id
                    team_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    
                    if team_score > opp_score: h_form_4.append('W')
                    elif team_score == opp_score: h_form_4.append('D')
                    else: h_form_4.append('L')
                    
                a_matches_all = [m for m in all_matches if m.home_team_id == away_id or m.away_team_id == away_id]
                a_matches_all.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                a_form_4 = []
                for m in a_matches_all[:4]:
                    is_home = m.home_team_id == away_id
                    team_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    
                    if team_score > opp_score: a_form_4.append('W')
                    elif team_score == opp_score: a_form_4.append('D')
                    else: a_form_4.append('L')

                # Calculate Over 2.5 % (Overall)
                h_over_count = sum(1 for m in h_matches_all if (m.home_score + m.away_score) > 2.5)
                h_over_pct = int((h_over_count / len(h_matches_all) * 100)) if h_matches_all else 0
                
                a_over_count = sum(1 for m in a_matches_all if (m.home_score + m.away_score) > 2.5)
                a_over_pct = int((a_over_count / len(a_matches_all) * 100)) if a_matches_all else 0

                entry = {
                    'match': match,
                    'home_team': match.home_team,
                    'away_team': match.away_team,
                    'h_ppg_pct': int((h_s['ppg'] / 3) * 100),
                    'a_ppg_pct': int((a_s['ppg'] / 3) * 100),
                    'h_wdl': {'w': h_s['w_pct'], 'd': h_s['d_pct'], 'l': h_s['l_pct']},
                    'a_wdl': {'w': a_s['w_pct'], 'd': a_s['d_pct'], 'l': a_s['l_pct']},
                    'h_goals': {'gf': round(h_s['gf_avg'], 2), 'ga': round(h_s['ga_avg'], 2), 'tg': round(h_s['tg_avg'], 2)},
                    'a_goals': {'gf': round(a_s['gf_avg'], 2), 'ga': round(a_s['ga_avg'], 2), 'tg': round(a_s['tg_avg'], 2)},
                    'h_over_25': h_over_pct,
                    'a_over_25': a_over_pct,
                    'h_last_4': h_form_4,
                    'a_last_4': a_form_4
                }
                stats_entries_overall.append(entry)

            # Prepare Statistics Tab Data (Last 8 Matches)
            stats_entries_last8 = []
            
            for match in upcoming_matches_qs:
                home_id = match.home_team_id
                away_id = match.away_team_id
                
                # Get last 8 matches for each team
                h_matches_all = [m for m in all_matches if m.home_team_id == home_id or m.away_team_id == home_id]
                h_matches_all.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                h_last8 = h_matches_all[:8]
                
                a_matches_all = [m for m in all_matches if m.home_team_id == away_id or m.away_team_id == away_id]
                a_matches_all.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                a_last8 = a_matches_all[:8]
                
                def calc_last8_stats(matches, team_id):
                    gp = len(matches)
                    if gp == 0:
                        return {'ppg': 0, 'w_pct': 0, 'd_pct': 0, 'l_pct': 0, 'gf_avg': 0, 'ga_avg': 0, 'tg_avg': 0}
                    
                    pts = 0; w = 0; d = 0; l = 0; gf = 0; ga = 0
                    for m in matches:
                        is_home = m.home_team_id == team_id
                        team_score = m.home_score if is_home else m.away_score
                        opp_score = m.away_score if is_home else m.home_score
                        
                        gf += team_score
                        ga += opp_score
                        
                        if team_score > opp_score: w += 1; pts += 3
                        elif team_score == opp_score: d +=1; pts += 1
                        else: l += 1
                        
                    return {
                        'ppg': pts / gp,
                        'w_pct': (w / gp) * 100,
                        'd_pct': (d / gp) * 100,
                        'l_pct': (l / gp) * 100,
                        'gf_avg': gf / gp,
                        'ga_avg': ga / gp,
                        'tg_avg': (gf + ga) / gp
                    }
                
                h_s = calc_last8_stats(h_last8, home_id)
                a_s = calc_last8_stats(a_last8, away_id)
                
                # Form (Last 4 of the Last 8 - effectively Last 4 overall)
                h_form_4 = []
                for m in h_last8[:4]:
                    is_home = m.home_team_id == home_id
                    team_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    if team_score > opp_score: h_form_4.append('W')
                    elif team_score == opp_score: h_form_4.append('D')
                    else: h_form_4.append('L')
                    
                a_form_4 = []
                for m in a_last8[:4]:
                    is_home = m.home_team_id == away_id
                    team_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    if team_score > opp_score: a_form_4.append('W')
                    elif team_score == opp_score: a_form_4.append('D')
                    else: a_form_4.append('L')
                
                # Over 2.5 % (in Last 8)
                h_over_count = sum(1 for m in h_last8 if (m.home_score + m.away_score) > 2.5)
                h_over_pct = int((h_over_count / len(h_last8) * 100)) if h_last8 else 0
                
                a_over_count = sum(1 for m in a_last8 if (m.home_score + m.away_score) > 2.5)
                a_over_pct = int((a_over_count / len(a_last8) * 100)) if a_last8 else 0

                entry = {
                    'match': match,
                    'home_team': match.home_team,
                    'away_team': match.away_team,
                    'h_ppg_pct': int((h_s['ppg'] / 3) * 100),
                    'a_ppg_pct': int((a_s['ppg'] / 3) * 100),
                    'h_wdl': {'w': h_s['w_pct'], 'd': h_s['d_pct'], 'l': h_s['l_pct']},
                    'a_wdl': {'w': a_s['w_pct'], 'd': a_s['d_pct'], 'l': a_s['l_pct']},
                    'h_goals': {'gf': round(h_s['gf_avg'], 2), 'ga': round(h_s['ga_avg'], 2), 'tg': round(h_s['tg_avg'], 2)},
                    'a_goals': {'gf': round(a_s['gf_avg'], 2), 'ga': round(a_s['ga_avg'], 2), 'tg': round(a_s['tg_avg'], 2)},
                    'h_over_25': h_over_pct,
                    'a_over_25': a_over_pct,
                    'h_last_4': h_form_4,
                    'a_last_4': a_form_4
                }
                stats_entries_last8.append(entry)
            
            context['stats_entries'] = stats_entries
            context['stats_entries_overall'] = stats_entries_overall
            context['stats_entries_last8'] = stats_entries_last8
            context['upcoming_matches'] = upcoming_matches_qs
        else:
            context['standings'] = []
            context['home_table'] = []
            context['away_table'] = []
            context['upcoming_matches'] = []
            
        return context



class TeamDetailView(DetailView):
    model = Team
    template_name = 'matches/team_detail.html'
    context_object_name = 'team'

    def get_object(self):
        # Captura os parâmetros da URL
        league_slug = self.kwargs.get('league_name')
        team_slug = self.kwargs.get('team_name')
        
        # Converte slugs para busca aproximada (ex: premier-league -> Premier League)
        # remove hífens e tenta buscar
        league_name_query = league_slug.replace('-', ' ')
        team_name_query = team_slug.replace('-', ' ')
        
        # Busca Liga
        league = get_object_or_404(League, name__icontains=league_name_query)
        
        # Busca Time (tenta nome exato, depois contem)
        team = Team.objects.filter(league=league, name__iexact=team_name_query).first()
        if not team:
             team = get_object_or_404(Team, league=league, name__icontains=team_name_query)
             
        return team

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.object
        league = team.league
        
        # Latest Season
        latest_season = Season.objects.filter(standings__league=league).order_by('-year').distinct().first()
        
        # League Standing
        standing = LeagueStanding.objects.filter(
            league=league, season=latest_season, team=team
        ).first()
        
        context['standing'] = standing
        context['league'] = league

        # --- Comparison with Past Seasons Logic ---
        past_seasons_data = []
        if standing:
            current_gp = standing.played
            current_pts = standing.points
            
            # Get past seasons (exclude current)
            past_seasons = Season.objects.filter(standings__league=league).exclude(id=latest_season.id).distinct().order_by('-year')
            
            for s_obj in past_seasons:
                # Get matches for this season involving the team
                season_matches = Match.objects.filter(
                    league=league,
                    season=s_obj,
                    status='Finished'
                ).filter(
                    models.Q(home_team=team) | models.Q(away_team=team)
                ).order_by('date')
                
                # Take the first 'current_gp' matches
                matches_subset = season_matches[:current_gp]
                gp = len(matches_subset)
                
                # Only include if there's at least one match to compare, 
                # though strictly we might want exactly 'current_gp'. 
                # We'll show what we have.
                if gp > 0:
                    w = 0; d = 0; l = 0; gf = 0; ga = 0; pts = 0
                    
                    for m in matches_subset:
                        is_home = m.home_team == team
                        my_score = m.home_score if is_home else m.away_score
                        opp_score = m.away_score if is_home else m.home_score
                        
                        # Handle potential None values safely
                        if my_score is None: my_score = 0
                        if opp_score is None: opp_score = 0
                        
                        gf += my_score
                        ga += opp_score
                        
                        if my_score > opp_score:
                            w += 1
                            pts += 3
                        elif my_score == opp_score:
                            d += 1
                            pts += 1
                        else:
                            l += 1
                    
                    # Comparison: Difference between CURRENT Pts and PAST Pts
                    # Example: Current 49, Past 51 -> Diff is -2. 
                    # Correct logic: Current - Past.
                    diff = current_pts - pts
                    
                    past_seasons_data.append({
                        'season_year': s_obj.year,
                        'gp': gp,
                        'w': w, 'd': d, 'l': l,
                        'gf': gf, 'ga': ga, 'pts': pts,
                        'diff': diff,
                        'is_partial': gp < current_gp
                    })
        
        context['past_seasons_data'] = past_seasons_data
        context['current_gp_comparison'] = current_gp if standing else 0

        
        # All Matches
        all_matches = Match.objects.filter(
             league=league, season=latest_season
         ).filter(
             models.Q(home_team=team) | models.Q(away_team=team)
         ).order_by('date')
         
        played_matches = [m for m in all_matches if m.status == 'Finished' and m.home_score is not None]
        
        # --- Stats Containers ---
        # Structure: 'home', 'away', 'total'
        cats = ['home', 'away', 'total']
        
        # Basic Stats
        stats = {c: {
            'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0,
            'win_margins': {}, 'loss_margins': {}, # Dicts to count margins
            'ht_w': 0, 'ht_d': 0, 'ht_l': 0,
            'corners_for_list': [], 'corners_against_list': []
        } for c in cats}
        
        # Goal Rates (Over/Under)
        thresholds = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
        ht_thresholds = [0.5, 1.5, 2.5]
        goal_stats = {
            'scored': {c: {t: 0 for t in thresholds} for c in cats},
            'conceded': {c: {t: 0 for t in thresholds} for c in cats},
            'match_total': {c: {t: 0 for t in thresholds} for c in cats},
            'ht_match_total': {c: {t: 0 for t in ht_thresholds} for c in cats}
        }
        
        # Special Rates
        rates = {c: {
            'cs': 0, 'fts': 0, 'bts': 0,
            'score_1h': 0, 'score_2h': 0, 'score_both': 0,
            'concede_1h': 0, 'concede_2h': 0, 'concede_both': 0
        } for c in cats}
        
        # Total Goals Distribution (exact goals)
        total_goals_dist = {c: {i: 0 for i in range(6)} for c in cats} # 0, 1, 2, 3, 4, 5+
        
        matches_data = [] # List for display
        chart_data = {'labels': [], 'values': [], 'results': [], 'gf': [], 'ga': []}
        chart_val = 0
        
        for m in played_matches:
            is_home = m.home_team == team
            cat = 'home' if is_home else 'away'
            
            gf = m.home_score if is_home else m.away_score
            ga = m.away_score if is_home else m.home_score
            
            # HT Scores (Assume None=0 if missing, though typically present)
            ht_gf = (m.ht_home_score if is_home else m.ht_away_score) or 0
            ht_ga = (m.ht_away_score if is_home else m.ht_home_score) or 0
            
            # 2nd Half Scores
            ft_gf_2h = gf - ht_gf
            ft_ga_2h = ga - ht_ga
            
            match_total = gf + ga
            result = 'W' if gf > ga else ('D' if gf == ga else 'L')
            opponent = m.away_team if is_home else m.home_team
            
            # --- Update Basic Stats ---
            for k in [cat, 'total']:
                s = stats[k]
                s['gp'] += 1
                s['gf'] += gf
                s['ga'] += ga
                if result == 'W': s['w'] += 1; s['pts'] += 3
                elif result == 'D': s['d'] += 1; s['pts'] += 1
                else: s['l'] += 1
                
                # Rates
                r = rates[k]
                if ga == 0: r['cs'] += 1
                if gf == 0: r['fts'] += 1
                if gf > 0 and ga > 0: r['bts'] += 1
                
                if ht_gf > 0: r['score_1h'] += 1
                if ft_gf_2h > 0: r['score_2h'] += 1
                if ht_gf > 0 and ft_gf_2h > 0: r['score_both'] += 1
                
                if ht_ga > 0: r['concede_1h'] += 1
                if ft_ga_2h > 0: r['concede_2h'] += 1
                if ht_ga > 0 and ft_ga_2h > 0: r['concede_both'] += 1

                # Goal Thresholds
                gs = goal_stats['scored'][k]
                gc = goal_stats['conceded'][k]
                gm = goal_stats['match_total'][k]
                ght = goal_stats['ht_match_total'][k]
                
                for t in thresholds:
                    if gf > t: gs[t] += 1
                    if ga > t: gc[t] += 1
                    if match_total > t: gm[t] += 1
                
                ht_match_total = ht_gf + ht_ga
                for t in ht_thresholds:
                    if ht_match_total > t: ght[t] += 1
                    
                # Exact Goals Dist
                tg_idx = match_total if match_total < 5 else 5
                total_goals_dist[k][tg_idx] += 1
                
                # Update Margins
                margin = abs(gf - ga)
                if result == 'W':
                    s['win_margins'][margin] = s['win_margins'].get(margin, 0) + 1
                elif result == 'L':
                    s['loss_margins'][margin] = s['loss_margins'].get(margin, 0) + 1
                    
                if ht_gf > ht_ga: s['ht_w'] += 1
                elif ht_gf == ht_ga: s['ht_d'] += 1
                else: s['ht_l'] += 1
                
                if m.home_corners is not None and m.away_corners is not None:
                    my_corners = m.home_corners if is_home else m.away_corners
                    opp_corners = m.away_corners if is_home else m.home_corners
                    s['corners_for_list'].append(my_corners)
                    s['corners_against_list'].append(opp_corners)

            # --- Match List Item ---
            matches_data.append({
                'date': m.date,
                'opponent': opponent,
                'is_home': is_home,
                'score': f"{m.home_score}-{m.away_score}",
                'ht_score': f"{m.ht_home_score}-{m.ht_away_score}" if m.ht_home_score is not None else "-",
                'result': result,
                'result_class': 'ss-green' if result == 'W' else ('ss-red' if result == 'L' else 'ss-orange'),
                'total_goals': match_total,
                'over_25': match_total > 2.5,
                'cs': ga == 0,
                'fts': gf == 0,
                'bts': gf > 0 and ga > 0
            })
            
            # --- Chart Data ---
            chart_change = 2 if result == 'W' else (0 if result == 'D' else -1)
            chart_val += chart_change
            chart_data['labels'].append(m.date.strftime('%d %b') if m.date else f"R{m.round}")
            chart_data['values'].append(chart_val)
            chart_data['results'].append(result)
            chart_data['gf'].append(gf)
            chart_data['ga'].append(-ga) # Negative for conceded


        # --- Helper for Percentages ---
        def calc_pct(val, gp):
            return round((val / gp) * 100) if gp > 0 else 0
            


        # Post-process Stats Dictionary
        for k in cats:
            gp = stats[k]['gp']
            stats[k]['ppg'] = round(stats[k]['pts'] / gp, 2) if gp > 0 else 0
            
            # Points Share
            total_pts = stats['total']['pts']
            stats[k]['points_pct_share'] = calc_pct(stats[k]['pts'], total_pts)

            stats[k]['avg_gf'] = round(stats[k]['gf'] / gp, 2) if gp > 0 else 0
            stats[k]['avg_ga'] = round(stats[k]['ga'] / gp, 2) if gp > 0 else 0
            stats[k]['win_pct'] = calc_pct(stats[k]['w'], gp)
            stats[k]['draw_pct'] = calc_pct(stats[k]['d'], gp)
            stats[k]['loss_pct'] = calc_pct(stats[k]['l'], gp)
            stats[k]['avg_total_goals'] = round(stats[k]['avg_gf'] + stats[k]['avg_ga'], 2)
            
            # Rates %
            for rk in list(rates[k].keys()):
                rates[k][rk + '_pct'] = calc_pct(rates[k][rk], gp)
            
            # Explicit Scoring/Conceding Rates (Complement of FTS/CS)
            rates[k]['scoring_rate_pct'] = 100 - rates[k]['fts_pct']
            rates[k]['conceding_rate_pct'] = 100 - rates[k]['cs_pct']
            
            # Goal Rates %
            for type_ in ['scored', 'conceded', 'match_total']:
                for t in thresholds:
                    goal_stats[type_][k][f"{t}_pct"] = calc_pct(goal_stats[type_][k][t], gp)
            
            # HT %
            for t in ht_thresholds:
                goal_stats['ht_match_total'][k][f"{t}_pct"] = calc_pct(goal_stats['ht_match_total'][k][t], gp)
            
            # Goals Dist %
            for i in range(6):
                total_goals_dist[k][f"{i}_pct"] = calc_pct(total_goals_dist[k][i], gp)
                
            # Margins %
            # (Calculated in context generally, but percentages can be done here if needed)

        # --- Post-Loop aggregated stats ---
        
        # Helper for Margin aggregation
        def get_margin_counts(data):
            return {
                1: data.get(1, 0),
                2: data.get(2, 0),
                3: data.get(3, 0),
                4: sum(v for k, v in data.items() if k >= 4)
            }
        
        margin_stats = {
            'wins': {
                'home': get_margin_counts(stats['home']['win_margins']),
                'away': get_margin_counts(stats['away']['win_margins']),
                'total': get_margin_counts(stats['total']['win_margins'])
            },
            'defeats': {
                'home': get_margin_counts(stats['home']['loss_margins']),
                'away': get_margin_counts(stats['away']['loss_margins']),
                'total': get_margin_counts(stats['total']['loss_margins'])
            }
        }
        
        # HT Results Percentages
        ht_stats = {
            'leading': {'home': stats['home']['ht_w'], 'away': stats['away']['ht_w'], 'total': stats['total']['ht_w']},
            'drawing': {'home': stats['home']['ht_d'], 'away': stats['away']['ht_d'], 'total': stats['total']['ht_d']},
            'losing': {'home': stats['home']['ht_l'], 'away': stats['away']['ht_l'], 'total': stats['total']['ht_l']},
        }
        for res in ht_stats:
            for c in cats:
                gp = stats[c]['gp']
                ht_stats[res][f"{c}_pct"] = calc_pct(ht_stats[res][c], gp)
        
        # Corner Stats Percentages & Avgs
        corner_thresholds = [2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5]
        corner_data = {
            'for': {c: {'avg': 0, 'thresholds': {t: 0 for t in corner_thresholds}} for c in cats},
            'against': {c: {'avg': 0, 'thresholds': {t: 0 for t in corner_thresholds}} for c in cats},
            'total': {c: {'avg': 0, 'thresholds': {t: 0 for t in corner_thresholds}} for c in cats}
        }
        
        for c in cats:
            gp = stats[c]['gp']
            corners_for = stats[c]['corners_for_list']
            corners_against = stats[c]['corners_against_list']
            valid_gp = len(corners_for)
            if gp > 0 and valid_gp > 0:
                total_corners = [x + y for x, y in zip(corners_for, corners_against)]
                corner_data['for'][c]['avg'] = round(sum(corners_for) / valid_gp, 2)
                for t in corner_thresholds:
                    count = sum(1 for x in corners_for if x > t)
                    corner_data['for'][c]['thresholds'][t] = calc_pct(count, valid_gp)
                corner_data['against'][c]['avg'] = round(sum(corners_against) / valid_gp, 2)
                for t in corner_thresholds:
                    count = sum(1 for x in corners_against if x > t)
                    corner_data['against'][c]['thresholds'][t] = calc_pct(count, valid_gp)
                corner_data['total'][c]['avg'] = round(sum(total_corners) / valid_gp, 2)
                for t in corner_thresholds:
                    count = sum(1 for x in total_corners if x > t)
                    corner_data['total'][c]['thresholds'][t] = calc_pct(count, valid_gp)
        
        context['margin_stats'] = margin_stats
        context['ht_stats'] = ht_stats
        context['corner_data'] = corner_data
        context['corner_thresholds'] = corner_thresholds

        context['stats'] = stats
        context['rates'] = rates
        context['goal_stats'] = goal_stats
        context['total_goals_dist'] = total_goals_dist
        context['thresholds'] = thresholds
        context['ht_thresholds'] = ht_thresholds
        # Últimos 20 jogos apenas (recorte da lista, em ordem do mais recente para o mais antigo)
        context['matches_list'] = matches_data[-20:][::-1]
        context['chart_data_json'] = json.dumps(chart_data)

        # --- League Averages for Descriptive Text ---
        league_matches = Match.objects.filter(league=league, season=latest_season, status='Finished', home_score__isnull=False)
        league_gp = league_matches.count()
        league_over25 = league_matches.annotate(total_g=models.F('home_score') + models.F('away_score')).filter(total_g__gt=2.5).count()
        league_over25_pct = round((league_over25 / league_gp) * 100) if league_gp > 0 else 0
        context['league_over25_pct'] = league_over25_pct
        
        # --- Relative Form ---
        # (Simplified reuse of existing logic or derived from played_matches)
        # Included in stats['total'] vs Last 8
        last_8 = played_matches[-8:]
        l8_pts = sum([3 if (m.home_team==team and m.home_score>m.away_score) or (m.away_team==team and m.away_score>m.home_score) else (1 if m.home_score==m.away_score else 0) for m in last_8])
        l8_gf = sum([(m.home_score if m.home_team==team else m.away_score) for m in last_8])
        l8_ga = sum([(m.away_score if m.home_team==team else m.home_score) for m in last_8])
        l8_gp = len(last_8)
        
        l8_ppg = round(l8_pts / l8_gp, 2) if l8_gp > 0 else 0
        l8_avg_gf = round(l8_gf / l8_gp, 2) if l8_gp > 0 else 0
        l8_avg_ga = round(l8_ga / l8_gp, 2) if l8_gp > 0 else 0
        
        season_ppg = stats['total']['ppg']
        season_avg_gf = stats['total']['avg_gf']
        season_avg_ga = stats['total']['avg_ga']
        
        def calc_diff(l8, season):
            if season == 0: return 0
            return round(((l8 - season) / season) * 100, 1)

        context['relative_form'] = {
            'ppg': {'all': season_ppg, 'l8': l8_ppg, 'diff': calc_diff(l8_ppg, season_ppg)},
            'avg_gf': {'all': season_avg_gf, 'l8': l8_avg_gf, 'diff': calc_diff(l8_avg_gf, season_avg_gf)},
            'avg_ga': {'all': season_avg_ga, 'l8': l8_avg_ga, 'diff': calc_diff(l8_avg_ga, season_avg_ga)},
        }

        # --- League Averages for Comparison Box ---
        # Get all teams in the league for this season
        all_league_standings = LeagueStanding.objects.filter(
            league=league,
            season=latest_season
        ).select_related('team')
        
        # Get all matches in the league for this season
        all_league_matches = Match.objects.filter(
            league=league,
            season=latest_season,
            status='Finished',
            home_score__isnull=False
        ).select_related('home_team', 'away_team')
        
        # Calculate league averages for each category (total, home, away)
        league_avg = {c: {
            'ppg': 0, 'win_pct': 0, 'draw_pct': 0, 'loss_pct': 0,
            'avg_gf': 0, 'avg_ga': 0, 'cs_pct': 0, 'fts_pct': 0,
            'wtn_pct': 0, 'ltn_pct': 0, 'scored_first_pct': 0, 'conceded_first_pct': 0,
            'avg_min_scored_first': 0, 'avg_min_conceded_first': 0
        } for c in cats}
        
        # Calculate stats for each team in the league
        team_count = all_league_standings.count()
        if team_count > 0:
            for standing in all_league_standings:
                league_team = standing.team
                team_matches = [m for m in all_league_matches if m.home_team == league_team or m.away_team == league_team]
                
                # Stats by category
                team_stats_calc = {c: {
                    'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0,
                    'cs': 0, 'fts': 0, 'wtn': 0, 'ltn': 0, 'scored_first': 0, 'conceded_first': 0,
                    'min_scored_first': [], 'min_conceded_first': []
                } for c in cats}
                
                for m in team_matches:
                    is_home = m.home_team == league_team
                    cat = 'home' if is_home else 'away'
                    
                    gf = m.home_score if is_home else m.away_score
                    ga = m.away_score if is_home else m.home_score
                    result = 'W' if gf > ga else ('D' if gf == ga else 'L')
                    
                    for k in [cat, 'total']:
                        s = team_stats_calc[k]
                        s['gp'] += 1
                        s['gf'] += gf
                        s['ga'] += ga
                        if result == 'W': s['w'] += 1; s['pts'] += 3
                        elif result == 'D': s['d'] += 1; s['pts'] += 1
                        else: s['l'] += 1
                        
                        # Special rates
                        if ga == 0: s['cs'] += 1
                        if gf == 0: s['fts'] += 1
                        if result == 'W' and ga == 0: s['wtn'] += 1
                        if result == 'L' and gf == 0: s['ltn'] += 1
                        
                        # First goal tracking (simplified - we'll use approximations)
                        # For now, assume team scored first if they won or drew and scored
                        if gf > 0:
                            if gf > ga or (gf == ga and gf > 0):
                                s['scored_first'] += 1
                                s['min_scored_first'].append(30)  # Approximate average
                        if ga > 0:
                            if ga > gf or (ga == gf and ga > 0):
                                s['conceded_first'] += 1
                                s['min_conceded_first'].append(35)  # Approximate average
                
                # Add to league averages
                for c in cats:
                    s = team_stats_calc[c]
                    gp = s['gp']
                    if gp > 0:
                        league_avg[c]['ppg'] += s['pts'] / gp
                        league_avg[c]['win_pct'] += (s['w'] / gp) * 100
                        league_avg[c]['draw_pct'] += (s['d'] / gp) * 100
                        league_avg[c]['loss_pct'] += (s['l'] / gp) * 100
                        league_avg[c]['avg_gf'] += s['gf'] / gp
                        league_avg[c]['avg_ga'] += s['ga'] / gp
                        league_avg[c]['cs_pct'] += (s['cs'] / gp) * 100
                        league_avg[c]['fts_pct'] += (s['fts'] / gp) * 100
                        league_avg[c]['wtn_pct'] += (s['wtn'] / gp) * 100
                        league_avg[c]['ltn_pct'] += (s['ltn'] / gp) * 100
                        league_avg[c]['scored_first_pct'] += (s['scored_first'] / gp) * 100
                        league_avg[c]['conceded_first_pct'] += (s['conceded_first'] / gp) * 100
                        if s['min_scored_first']:
                            league_avg[c]['avg_min_scored_first'] += sum(s['min_scored_first']) / len(s['min_scored_first'])
                        if s['min_conceded_first']:
                            league_avg[c]['avg_min_conceded_first'] += sum(s['min_conceded_first']) / len(s['min_conceded_first'])
            
            # Calculate final averages
            for c in cats:
                for key in league_avg[c]:
                    league_avg[c][key] = round(league_avg[c][key] / team_count, 2)
        
        context['league_avg'] = league_avg

        # --- Player Stats (Top Scorers) ---
        from .models import Goal, Player
        from django.db.models import Count
        
        # Get goals for this team in this season
        # Filter matches first to get IDs
        match_ids = [m.id for m in all_matches]
        
        top_scorers = Goal.objects.filter(
            team=team,
            match__id__in=match_ids
        ).values('player_name').annotate(total=Count('id')).order_by('-total')[:15]
        
        # For each scorer, get home/away split (a bit expensive with loop queries but ok for 15 rows)
        players_data = []
        # PPG Calculation
        def calc_ppg(w, d, gp):
            if gp == 0: return 0
            return round(((w * 3) + d) / gp, 2)
        
        stats['home']['ppg'] = calc_ppg(stats['home']['w'], stats['home']['d'], stats['home']['gp'])
        stats['away']['ppg'] = calc_ppg(stats['away']['w'], stats['away']['d'], stats['away']['gp'])
        stats['total']['ppg'] = calc_ppg(stats['total']['w'], stats['total']['d'], stats['total']['gp'])

        # W/D/L Percentages for segmented bars
        for c in cats:
            gp = stats[c]['gp']
            if gp > 0:
                stats[c]['w_pct'] = (stats[c]['w'] / gp) * 100
                stats[c]['d_pct'] = (stats[c]['d'] / gp) * 100
                stats[c]['l_pct'] = (stats[c]['l'] / gp) * 100
            else:
                stats[c]['w_pct'] = stats[c]['d_pct'] = stats[c]['l_pct'] = 0

        total_team_goals = stats['total']['gf']
        
        for p in top_scorers:
            name = p['player_name']
            total = p['total']
            
            # Simple hack: count home/away via Python filtering of specific goal objects?
            # Better: separate aggregation. But for now, let's keep it simple.
            # We can run a second query for home goals.
            home_goals = Goal.objects.filter(team=team, match__id__in=match_ids, player_name=name, match__home_team=team).count()
            away_goals = total - home_goals
            
            # Get Last Goal Date
            last_goal = Goal.objects.filter(team=team, match__id__in=match_ids, player_name=name).select_related('match').order_by('-match__date').first()
            last_goal_date = last_goal.match.date if last_goal and last_goal.match.date else None
            
            # Get Player Details (Age, Nationality)
            player_obj = Player.objects.filter(team=team, name__iexact=name).first()
            age = player_obj.age if player_obj else "-"
            nationality = player_obj.nationality if player_obj else None

            players_data.append({
                'name': name,
                'total': total,
                'home': home_goals,
                'away': away_goals,
                'last_date': last_goal_date,
                'age': age,
                'nationality': nationality,
                'pct': round((total / total_team_goals * 100)) if total_team_goals > 0 else 0
            })
            
        context['top_scorers'] = players_data
        
        # --- League Standings (Results Table) ---
        standings_qs = LeagueStanding.objects.filter(
            league=league,
            season=latest_season
        ).select_related('team').order_by('position')[:20]
        
        # Prepare h2h data for the standings table
        h2h_map = {}
        # We use all_matches which is already filtered for just our team and already selected above
        for m in all_matches:
            if m.home_team == team:
                h2h_map.setdefault(m.away_team_id, {})['home'] = m
            else:
                h2h_map.setdefault(m.home_team_id, {})['away'] = m
        
        league_h2h = []
        for st in standings_qs:
            opp_id = st.team_id
            m_h = h2h_map.get(opp_id, {}).get('home')
            m_a = h2h_map.get(opp_id, {}).get('away')
            
            def format_h2h(m, is_home):
                if not m: return {'score': '-', 'bg': ''}
                if m.home_score is None: 
                    return {'score': m.date.strftime('%d %b'), 'bg': ''}
                
                # Check result from our team's view
                if is_home:
                    won = m.home_score > m.away_score
                    lost = m.home_score < m.away_score
                else:
                    won = m.away_score > m.home_score
                    lost = m.away_score < m.home_score
                
                bg = 'row-win' if won else ('row-loss' if lost else 'row-draw')
                return {'score': f"{m.home_score}:{m.away_score}", 'bg': bg}

            league_h2h.append({
                'standing': st,
                'home': format_h2h(m_h, True),
                'away': format_h2h(m_a, False)
            })

        context['league_h2h'] = league_h2h
        context['thresholds'] = thresholds
        context['cats'] = cats

        # --- NEW: Current Streaks ---
        context['streaks'] = self.calculate_streaks(all_matches, team)

        # --- NEW: Historical Statistics (Current vs Prev Season) ---
        # We need the previous season object. We already fetched past_seasons.
        prev_season_data = None
        if past_seasons:
            prev_season = past_seasons[0] # Assuming ordered by -year
            
            # Helper to calculate stats for a given season and matches
            def calc_historical(matches_qs, t):
                stats = {'pld': 0, 'pts': 0, 'gf': 0, 'ga': 0, 'w': 0, 'd': 0, 'l': 0, 'cs': 0, 'fts': 0}
                if not matches_qs: return stats
                stats['pld'] = len(matches_qs)
                for m in matches_qs:
                    is_home = m.home_team == t
                    my_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    
                    if my_score is None or opp_score is None: continue # Skip played but no score? (status check done in filter)
                    
                    stats['gf'] += my_score
                    stats['ga'] += opp_score
                    
                    if my_score > opp_score: 
                        stats['w'] += 1
                        stats['pts'] += 3
                    elif my_score == opp_score: 
                        stats['d'] += 1
                        stats['pts'] += 1
                    else: 
                        stats['l'] += 1
                        
                    if opp_score == 0: stats['cs'] += 1
                    if my_score == 0: stats['fts'] += 1
                
                # Averages/Percents
                if stats['pld'] > 0:
                    stats['avg_pts'] = stats['pts'] / stats['pld']
                    stats['avg_gf'] = stats['gf'] / stats['pld']
                    stats['avg_ga'] = stats['ga'] / stats['pld']
                    stats['w_pct'] = int((stats['w'] / stats['pld']) * 100)
                    stats['d_pct'] = int((stats['d'] / stats['pld']) * 100)
                    stats['l_pct'] = int((stats['l'] / stats['pld']) * 100)
                    stats['cs_pct'] = int((stats['cs'] / stats['pld']) * 100)
                    stats['fts_pct'] = int((stats['fts'] / stats['pld']) * 100)
                return stats

            # Current Season Stats
            current_stats = {
                'overall': calc_historical(all_matches, team),
                'home': calc_historical([m for m in all_matches if m.home_team == team], team),
                'away': calc_historical([m for m in all_matches if m.away_team == team], team)
            }
            
            # Previous Season Stats
            prev_matches = Match.objects.filter(
                models.Q(home_team=team) | models.Q(away_team=team),
                season=prev_season,
                status='Finished'
            )
            previous_stats = {
                'overall': calc_historical(prev_matches, team),
                'home': calc_historical([m for m in prev_matches if m.home_team == team], team),
                'away': calc_historical([m for m in prev_matches if m.away_team == team], team)
            }
            
            context['historical_stats'] = {
                'current': current_stats,
                'previous': previous_stats,
                'season_name': f"{latest_season.year-1}/{latest_season.year}",
                'prev_season_name': f"{prev_season.year-1}/{prev_season.year}"
            }

        # --- Upcoming Matches & Run-in Analysis ---
        upcoming_matches = Match.objects.filter(
            models.Q(home_team=team) | models.Q(away_team=team),
            status='Scheduled',
            date__gte=datetime.now()
        ).order_by('date')
        
        run_in_data = []
        sum_opp_ppg_home = 0
        sum_opp_ppg_away = 0
        remaining_home = 0
        remaining_away = 0

        # Helper to get opponent PPG (using current season stats)
        # We need a robust way to get opponent stats. 
        # Ideally, we'd have a helper method or cache. 
        # For now, let's just calc it on the fly or use a simplified approach.
        # IMPROVEMENT: Use the 'current_stats' logic but for opponent.
        
        def get_team_ppg(t, is_home_venue):
             # Calculate opponent stats for specific venue
            opp_matches = Match.objects.filter(season=latest_season, status='Finished')
            if is_home_venue:
                opp_matches = opp_matches.filter(home_team=t)
                pts = 0
                pld = 0
                for om in opp_matches:
                    pld += 1
                    if om.home_score > om.away_score: pts += 3
                    elif om.home_score == om.away_score: pts += 1
                return round(pts / pld, 2) if pld > 0 else 0
            else:
                opp_matches = opp_matches.filter(away_team=t)
                pts = 0
                pld = 0
                for om in opp_matches:
                    pld += 1
                    if om.away_score > om.home_score: pts += 3
                    elif om.away_score == om.home_score: pts += 1
                return round(pts / pld, 2) if pld > 0 else 0

        for m in upcoming_matches:
            is_home = m.home_team == team
            opponent = m.away_team if is_home else m.home_team
            
            # Context: Stats for US
            my_stats = current_stats['home'] if is_home else current_stats['away']
            my_ppg = my_stats.get('avg_pts', 0)
            
            # Context: Stats for OPPONENT
            # If we are Home, Opponent is Away. We want Opponent's Away PPG.
            opp_venue_is_home = not is_home
            opp_ppg = get_team_ppg(opponent, opp_venue_is_home)
            
            # For table columns
            if is_home:
                col_home_ppg = f"{my_ppg:.2f}"
                col_away_ppg = f"{opp_ppg:.2f}"
                remaining_home += 1
                sum_opp_ppg_home += opp_ppg
            else:
                col_home_ppg = f"{opp_ppg:.2f}"
                col_away_ppg = f"{my_ppg:.2f}"
                remaining_away += 1
                sum_opp_ppg_away += opp_ppg

            run_in_data.append({
                'match': m,
                'is_home': is_home,
                'opponent': opponent,
                'col_home_ppg': col_home_ppg,
                'col_away_ppg': col_away_ppg,
                'opp_strength_pct': min(100, int((opp_ppg / 3.0) * 100))
            })

        avg_opp_ppg_home = round(sum_opp_ppg_home / remaining_home, 2) if remaining_home > 0 else 0
        avg_opp_ppg_away = round(sum_opp_ppg_away / remaining_away, 2) if remaining_away > 0 else 0
        avg_total_opp_ppg = round((sum_opp_ppg_home + sum_opp_ppg_away) / (remaining_home + remaining_away), 2) if (remaining_home + remaining_away) > 0 else 0

        context['run_in'] = {
            'matches': run_in_data,
            'avg_opp_ppg_home': avg_opp_ppg_home,
            'avg_opp_ppg_away': avg_opp_ppg_away,
            'avg_total_opp_ppg': avg_total_opp_ppg,
            'analysis': "Analysis placeholder..." # We can elaborate this later or use the template logic
        }

        return context

    def calculate_streaks(self, all_matches_qs, team):
        # We need finished matches sorted by date (most recent LAST) to iterate backwards easily
        # or most recent FIRST. Let's ensure order.
        # all_matches_qs is ordered by 'date' (asc)
        
        matches = [m for m in all_matches_qs if m.status == 'Finished' and m.home_score is not None]
        
        # Helper to get streaks
        def get_seq(match_list, condition_func):
            count = 0
            # Iterate backwards (newest to oldest)
            for m in reversed(match_list):
                if condition_func(m):
                    count += 1
                else:
                    break
            return count

        home_matches = [m for m in matches if m.home_team == team]
        away_matches = [m for m in matches if m.away_team == team]
        
        categories = {'total': matches, 'home': home_matches, 'away': away_matches}
        result = {}

        for cat, m_list in categories.items():
            # Define conditions
            # Helper for scores to handle None
            def scores(m):
                h = m.home_score if m.home_score is not None else 0
                a = m.away_score if m.away_score is not None else 0
                return (h, a)

            is_win = lambda m: (m.home_team == team and scores(m)[0] > scores(m)[1]) or \
                               (m.away_team == team and scores(m)[1] > scores(m)[0])
            
            is_draw = lambda m: scores(m)[0] == scores(m)[1]
            
            is_loss = lambda m: (m.home_team == team and scores(m)[0] < scores(m)[1]) or \
                                (m.away_team == team and scores(m)[1] < scores(m)[0])
            
            # No Win (Draw or Loss) -> NOT Win
            is_no_win = lambda m: not is_win(m)
            
            # No Draw -> Win or Loss
            is_no_draw = lambda m: not is_draw(m)
            
            # No Defeat -> Win or Draw
            is_no_defeat = lambda m: not is_loss(m)
            
            # 1 goal or more (Scored)
            scored_1plus = lambda m: (scores(m)[0] if m.home_team == team else scores(m)[1]) >= 1
            
            # 1 goal conceded or more
            conceded_1plus = lambda m: (scores(m)[1] if m.home_team == team else scores(m)[0]) >= 1
            
            # No goal scored (0)
            no_goal_scored = lambda m: (scores(m)[0] if m.home_team == team else scores(m)[1]) == 0
            
            # No goal conceded (Clean Sheet)
            no_goal_conceded = lambda m: (scores(m)[1] if m.home_team == team else scores(m)[0]) == 0
            
            # GF+GA over 2.5
            over_25 = lambda m: sum(scores(m)) > 2.5
            
            # GF+GA under 2.5
            under_25 = lambda m: sum(scores(m)) < 2.5
            
            # Scored at least twice
            scored_2plus = lambda m: (scores(m)[0] if m.home_team == team else scores(m)[1]) >= 2

            result[cat] = {
                'win': get_seq(m_list, is_win),
                'draw': get_seq(m_list, is_draw),
                'loss': get_seq(m_list, is_loss),
                'no_win': get_seq(m_list, is_no_win),
                'no_draw': get_seq(m_list, is_no_draw),
                'no_defeat': get_seq(m_list, is_no_defeat),
                'scored_1plus': get_seq(m_list, scored_1plus),
                'conceded_1plus': get_seq(m_list, conceded_1plus),
                'no_goal_scored': get_seq(m_list, no_goal_scored),
                'no_goal_conceded': get_seq(m_list, no_goal_conceded),
                'over_25': get_seq(m_list, over_25),
                'under_25': get_seq(m_list, under_25),
                'scored_2plus': get_seq(m_list, scored_2plus),
            }
            
        return result
