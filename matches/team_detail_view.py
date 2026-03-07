from django.views.generic import DetailView
from django.db import models
from .models import Team, Match, League

class TeamDetailView(DetailView):
    model = Team
    template_name = 'matches/team_detail.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.object
        
        # Get all finished matches for this team
        matches = Match.objects.filter(
            models.Q(home_team=team) | models.Q(away_team=team),
            status='Finished'
        ).order_by('-date', '-id')

        # Initialize comprehensive stats
        total_played = matches.count()
        wins = draws = losses = 0
        gf = ga = 0
        clean_sheets = failed_to_score = 0
        btts_count = over_25_count = 0
        
        # Home/Away breakdown
        home_stats = {'played': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'cs': 0, 'fts': 0}
        away_stats = {'played': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'cs': 0, 'fts': 0}
        
        # Goals by period (0-15, 16-30, 31-45, 46-60, 61-75, 76-90+)
        goals_by_period = {'scored': [0]*6, 'conceded': [0]*6}
        
        # Streaks
        current_streak = {'type': None, 'count': 0}
        longest_win_streak = longest_unbeaten = 0
        temp_win_streak = temp_unbeaten = 0
        
        form_history = []

        for m in matches:
            is_home = (m.home_team == team)
            score_for = m.home_score if is_home else m.away_score
            score_against = m.away_score if is_home else m.home_score
            
            # Basic stats
            gf += score_for
            ga += score_against
            
            if score_against == 0:
                clean_sheets += 1
                if is_home: home_stats['cs'] += 1
                else: away_stats['cs'] += 1
                
            if score_for == 0:
                failed_to_score += 1
                if is_home: home_stats['fts'] += 1
                else: away_stats['fts'] += 1
            
            # BTTS and Over 2.5
            if score_for > 0 and score_against > 0:
                btts_count += 1
            if (score_for + score_against) > 2.5:
                over_25_count += 1

            # Result tracking
            if score_for > score_against:
                wins += 1
                result = 'W'
                temp_win_streak += 1
                temp_unbeaten += 1
                if is_home: home_stats['w'] += 1
                else: away_stats['w'] += 1
            elif score_for == score_against:
                draws += 1
                result = 'D'
                temp_win_streak = 0
                temp_unbeaten += 1
                if is_home: home_stats['d'] += 1
                else: away_stats['d'] += 1
            else:
                losses += 1
                result = 'L'
                temp_win_streak = 0
                temp_unbeaten = 0
                if is_home: home_stats['l'] += 1
                else: away_stats['l'] += 1
            
            # Update longest streaks
            longest_win_streak = max(longest_win_streak, temp_win_streak)
            longest_unbeaten = max(longest_unbeaten, temp_unbeaten)
            
            # Current streak (most recent match)
            if not current_streak['type']:
                current_streak = {'type': result, 'count': 1}
            elif current_streak['type'] == result:
                current_streak['count'] += 1
            
            form_history.append(result)
            
            # Home/Away stats
            if is_home:
                home_stats['played'] += 1
                home_stats['gf'] += score_for
                home_stats['ga'] += score_against
            else:
                away_stats['played'] += 1
                away_stats['gf'] += score_for
                away_stats['ga'] += score_against

        # Helper to calculate percentages
        def calculate_pct(stats_dict):
            played = stats_dict['played']
            if played > 0:
                stats_dict['win_pct'] = round((stats_dict['w'] / played) * 100, 1)
                stats_dict['w_pct'] = stats_dict['win_pct']
                stats_dict['draw_pct'] = round((stats_dict['d'] / played) * 100, 1)
                stats_dict['d_pct'] = stats_dict['draw_pct']
                stats_dict['loss_pct'] = round((stats_dict['l'] / played) * 100, 1)
                stats_dict['l_pct'] = stats_dict['loss_pct']
                stats_dict['avg_gf'] = round(stats_dict['gf'] / played, 2)
                stats_dict['avg_ga'] = round(stats_dict['ga'] / played, 2)
                
                # PPG
                points = stats_dict['w'] * 3 + stats_dict['d']
                stats_dict['ppg'] = round(points / played, 2)
            else:
                stats_dict.update({
                    'win_pct': 0, 'w_pct': 0,
                    'draw_pct': 0, 'd_pct': 0,
                    'loss_pct': 0, 'l_pct': 0,
                    'avg_gf': 0, 'avg_ga': 0,
                    'ppg': 0
                })
            # Add GP/Played aliases
            stats_dict['gp'] = played
            return stats_dict

        home_stats = calculate_pct(home_stats)
        away_stats = calculate_pct(away_stats)
        
        total_stats = {
            'played': total_played,
            'w': wins,
            'd': draws,
            'l': losses,
            'gf': gf,
            'ga': ga
        }
        total_stats = calculate_pct(total_stats)
        
        # Add extra total stats
        total_stats.update({
            'gd': gf - ga,
            'clean_sheets': clean_sheets,
            'failed_to_score': failed_to_score,
            'cs_rate': round((clean_sheets / total_played) * 100, 1) if total_played else 0,
            'fts_rate': round((failed_to_score / total_played) * 100, 1) if total_played else 0,
            'btts_rate': round((btts_count / total_played) * 100, 1) if total_played else 0,
            'over_25_rate': round((over_25_count / total_played) * 100, 1) if total_played else 0,
        })

        # Structured stats for template
        context['stats'] = {
            'home': home_stats,
            'away': away_stats,
            'total': total_stats
        }
        context['cats'] = ['home', 'away', 'total']
        
        # League Averages
        league_matches = Match.objects.filter(
            league=team.league, 
            season=matches.first().season if matches.exists() else None,
            status='Finished'
        )
        
        if not league_matches.exists() and matches.exists():
             league_matches = Match.objects.filter(league=team.league, status='Finished')

        league_total_matches = league_matches.count()
        if league_total_matches > 0:
            l_home_wins = league_matches.filter(home_score__gt=models.F('away_score')).count()
            l_away_wins = league_matches.filter(away_score__gt=models.F('home_score')).count()
            l_draws = league_matches.filter(home_score=models.F('away_score')).count()
            
            l_home_goals = league_matches.aggregate(s=models.Sum('home_score'))['s'] or 0
            l_away_goals = league_matches.aggregate(s=models.Sum('away_score'))['s'] or 0
            l_total_goals = l_home_goals + l_away_goals
            
            total_team_games = league_total_matches * 2
            
            league_avg_total = {
                'win_pct': round(((l_home_wins + l_away_wins) / total_team_games) * 100, 1),
                'draw_pct': round(((l_draws * 2) / total_team_games) * 100, 1),
                'loss_pct': round(((l_home_wins + l_away_wins) / total_team_games) * 100, 1),
                'avg_gf': round(l_total_goals / total_team_games, 2),
                'avg_ga': round(l_total_goals / total_team_games, 2)
            }
            
            league_avg_home = {
                'win_pct': round((l_home_wins / league_total_matches) * 100, 1),
                'draw_pct': round((l_draws / league_total_matches) * 100, 1),
                'loss_pct': round((l_away_wins / league_total_matches) * 100, 1),
                'avg_gf': round(l_home_goals / league_total_matches, 2),
                'avg_ga': round(l_away_goals / league_total_matches, 2)
            }
            
            league_avg_away = {
                'win_pct': round((l_away_wins / league_total_matches) * 100, 1),
                'draw_pct': round((l_draws / league_total_matches) * 100, 1),
                'loss_pct': round((l_home_wins / league_total_matches) * 100, 1),
                'avg_gf': round(l_away_goals / league_total_matches, 2),
                'avg_ga': round(l_home_goals / league_total_matches, 2)
            }
            
            context['league_avg'] = {
                'home': league_avg_home,
                'away': league_avg_away,
                'total': league_avg_total
            }
        else:
             context['league_avg'] = {'home': {}, 'away': {}, 'total': {}}

        # Legacy context variables for backward compatibility if needed (though we should migrate template)
        context['home_stats'] = home_stats
        context['away_stats'] = away_stats
        context['current_streak'] = current_streak
        context['longest_win_streak'] = longest_win_streak
        context['longest_unbeaten'] = longest_unbeaten
        context['matches'] = matches[:20]  # Last 20 matches
        context['form_history'] = form_history[:10]  # Last 10 for form display
        
        return context
