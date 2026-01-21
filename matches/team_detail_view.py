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

        # Calculate percentages and averages
        context['stats'] = {
            'played': total_played,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'gf': gf,
            'ga': ga,
            'gd': gf - ga,
            'avg_gf': round(gf / total_played, 2) if total_played else 0,
            'avg_ga': round(ga / total_played, 2) if total_played else 0,
            'clean_sheets': clean_sheets,
            'failed_to_score': failed_to_score,
            'cs_rate': round((clean_sheets / total_played) * 100, 1) if total_played else 0,
            'fts_rate': round((failed_to_score / total_played) * 100, 1) if total_played else 0,
            'btts_rate': round((btts_count / total_played) * 100, 1) if total_played else 0,
            'over_25_rate': round((over_25_count / total_played) * 100, 1) if total_played else 0,
            'ppg': round((wins * 3 + draws) / total_played, 2) if total_played else 0,
        }
        
        # Home/Away PPG
        home_stats['ppg'] = round((home_stats['w'] * 3 + home_stats['d']) / home_stats['played'], 2) if home_stats['played'] else 0
        away_stats['ppg'] = round((away_stats['w'] * 3 + away_stats['d']) / away_stats['played'], 2) if away_stats['played'] else 0
        
        context['home_stats'] = home_stats
        context['away_stats'] = away_stats
        context['current_streak'] = current_streak
        context['longest_win_streak'] = longest_win_streak
        context['longest_unbeaten'] = longest_unbeaten
        context['matches'] = matches[:20]  # Last 20 matches
        context['form_history'] = form_history[:10]  # Last 10 for form display
        
        return context
