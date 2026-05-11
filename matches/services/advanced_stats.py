from django.db.models import Q
from matches.models import Match

class MatchAnalyzer:
    """
    Engine para calcular estatísticas avançadas, probabilidades e encontrar
    apostas de valor baseadas no histórico recente das equipes.
    """
    def __init__(self, match):
        self.match = match
        self.home_team = match.home_team
        self.away_team = match.away_team
        
        # Histórico recente (Últimos 10 jogos no geral)
        self.home_last_10 = self._get_recent_matches(self.home_team, limit=10)
        self.away_last_10 = self._get_recent_matches(self.away_team, limit=10)
        
        # Histórico específico (Últimos 10 em Casa para Mandante, Fora para Visitante)
        self.home_last_10_home = self._get_recent_matches(self.home_team, is_home=True, limit=10)
        self.away_last_10_away = self._get_recent_matches(self.away_team, is_away=True, limit=10)

    def _get_recent_matches(self, team, is_home=None, is_away=None, limit=10):
        # We only want matches that are finished (have scores) and happened before this match
        # If this match doesn't have a date, we use all past matches.
        qs = Match.objects.filter(
            home_score__isnull=False,
            away_score__isnull=False
        )
        
        if self.match.date:
            qs = qs.filter(date__lt=self.match.date)
            
        if is_home:
            qs = qs.filter(home_team=team)
        elif is_away:
            qs = qs.filter(away_team=team)
        else:
            qs = qs.filter(Q(home_team=team) | Q(away_team=team))
            
        return qs.order_by('-date')[:limit]

    def _calc_win_draw_loss(self, matches, team):
        w = d = l = 0
        gf = ga = 0
        total = len(matches)
        if total == 0:
            return {'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'total': 0, 'win_pct': 0}
            
        for m in matches:
            is_home = (m.home_team_id == team.id)
            score_for = m.home_score if is_home else m.away_score
            score_against = m.away_score if is_home else m.home_score
            
            gf += score_for
            ga += score_against
            
            if score_for > score_against:
                w += 1
            elif score_for == score_against:
                d += 1
            else:
                l += 1
                
        return {
            'w': w, 'd': d, 'l': l, 
            'gf': gf, 'ga': ga, 
            'avg_gf': round(gf / total, 2),
            'avg_ga': round(ga / total, 2),
            'total': total, 
            'win_pct': int((w / total) * 100),
            'loss_pct': int((l / total) * 100)
        }

    def get_general_form(self):
        home_form = self._calc_win_draw_loss(self.home_last_10, self.home_team)
        away_form = self._calc_win_draw_loss(self.away_last_10, self.away_team)
        return {'home': home_form, 'away': away_form}
        
    def get_specific_form(self):
        home_form = self._calc_win_draw_loss(self.home_last_10_home, self.home_team)
        away_form = self._calc_win_draw_loss(self.away_last_10_away, self.away_team)
        return {'home': home_form, 'away': away_form}

    def _eval_strength(self, avg_goals):
        if avg_goals >= 1.6:
            return "Strong"
        elif avg_goals >= 1.0:
            return "Average"
        return "Weak"

    def get_team_strength(self):
        general = self.get_general_form()
        home_avg_gf = general['home']['avg_gf']
        home_avg_ga = general['home']['avg_ga']
        away_avg_gf = general['away']['avg_gf']
        away_avg_ga = general['away']['avg_ga']
        
        return {
            'home_attack': self._eval_strength(home_avg_gf),
            'home_defense': self._eval_strength(2.5 - home_avg_ga), # Inverse metric
            'away_attack': self._eval_strength(away_avg_gf),
            'away_defense': self._eval_strength(2.5 - away_avg_ga)
        }

    def get_goal_markets(self):
        # Calculate Over probabilities based on specific forms
        def calc_over(matches, target):
            if not matches: return 0
            count = sum(1 for m in matches if (m.home_score + m.away_score) > target)
            return int((count / len(matches)) * 100)
            
        def calc_btts(matches):
            if not matches: return 0
            count = sum(1 for m in matches if m.home_score > 0 and m.away_score > 0)
            return int((count / len(matches)) * 100)
            
        def calc_ht_goal(matches):
            if not matches: return 0
            count = 0
            valid_matches = 0
            for m in matches:
                if m.ht_home_score is not None and m.ht_away_score is not None:
                    valid_matches += 1
                    if (m.ht_home_score + m.ht_away_score) > 0:
                        count += 1
            if valid_matches == 0: return 0
            return int((count / valid_matches) * 100)

        # We blend general form of both teams
        combined_matches = list(self.home_last_10) + list(self.away_last_10)
        
        # Chance de Marcar Primeiro (Últimos 10 jogos)
        def calc_first_to_score(matches, team):
            if not matches: return 0
            count = 0
            # Note: We need incidents or a flag. Since we don't have incidents, 
            # we use 'ht_home_score' and 'ht_away_score' as a proxy, 
            # or just look at teams that scored at least one.
            # Ideal: Check if team scored before the opponent.
            # Simplified for now: % of games team scored at least one goal.
            count = sum(1 for m in matches if (m.home_team_id == team.id and m.home_score > 0) or (m.away_team_id == team.id and m.away_score > 0))
            return int((count / len(matches)) * 100)

        return {
            'over_05': calc_over(combined_matches, 0.5),
            'over_15': calc_over(combined_matches, 1.5),
            'over_25': calc_over(combined_matches, 2.5),
            'over_35': calc_over(combined_matches, 3.5),
            'btts': calc_btts(combined_matches),
            'ht_goal': calc_ht_goal(combined_matches),
            'home_first_score': calc_first_to_score(self.home_last_10, self.home_team),
            'away_first_score': calc_first_to_score(self.away_last_10, self.away_team),
        }

    def get_match_odds_probs(self):
        # Calcula probabilidades de vitória baseadas no aproveitamento
        home_stats = self._calc_win_draw_loss(self.home_last_10_home, self.home_team)
        away_stats = self._calc_win_draw_loss(self.away_last_10_away, self.away_team)
        
        # Probabilidade simples baseada no histórico (Home Win / Draw / Away Win)
        # Usamos uma média entre geral e específico
        h_gen = self._calc_win_draw_loss(self.home_last_10, self.home_team)['win_pct']
        a_gen = self._calc_win_draw_loss(self.away_last_10, self.away_team)['win_pct']
        
        prob_home = (h_gen + home_stats['win_pct']) // 2
        prob_away = (a_gen + away_stats['win_pct']) // 2
        prob_draw = 100 - prob_home - prob_away
        if prob_draw < 0: prob_draw = 10
        
        # Re-ajusta para somar 100
        total = prob_home + prob_away + prob_draw
        prob_home = int((prob_home / total) * 100)
        prob_away = int((prob_away / total) * 100)
        prob_draw = int((prob_draw / total) * 100)
        
        return {
            'home_win': prob_home,
            'draw': prob_draw,
            'away_win': prob_away,
            'double_home': prob_home + prob_draw,
            'double_away': prob_away + prob_draw,
            'best_bet': "1" if prob_home > 50 else ("2" if prob_away > 50 else "X"),
            'double_bet': "1X" if prob_home + prob_draw > 70 else ("X2" if prob_away + prob_draw > 70 else "12")
        }

    def get_corner_markets(self):
        # Corner calculations
        def get_corner_stats(matches, team):
            scored = 0
            conceded = 0
            valid_matches = 0
            overs = {6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0}
            
            for m in matches:
                if m.home_corners is not None and m.away_corners is not None:
                    valid_matches += 1
                    is_home = (m.home_team_id == team.id)
                    team_c = m.home_corners if is_home else m.away_corners
                    opp_c = m.away_corners if is_home else m.home_corners
                    
                    scored += team_c
                    conceded += opp_c
                    total_c = team_c + opp_c
                    
                    for k in overs.keys():
                        if total_c > k:
                            overs[k] += 1
            
            if valid_matches == 0:
                return {'has_data': False, 'avg_scored': 0, 'avg_conceded': 0, 'avg_total': 0, 'overs': {k: 0 for k in overs.keys()}}
                
            return {
                'has_data': True,
                'avg_scored': round(scored / valid_matches, 2),
                'avg_conceded': round(conceded / valid_matches, 2),
                'avg_total': round((scored + conceded) / valid_matches, 2),
                'overs': {k: int((v / valid_matches) * 100) for k, v in overs.items()}
            }
            
        home_corners = get_corner_stats(self.home_last_10_home, self.home_team)
        away_corners = get_corner_stats(self.away_last_10_away, self.away_team)
        
        # Blend probabilities for the match
        match_overs = {}
        match_unders = {}
        for k in home_corners['overs'].keys():
            match_overs[k] = int((home_corners['overs'][k] + away_corners['overs'][k]) / 2)
            match_unders[k] = 100 - match_overs[k]
            
        # Basic recommendation logic (e.g., highest line with >= 70% probability)
        recommendation = "No clear suggestion"
        for k in sorted(match_overs.keys(), reverse=True):
            if match_overs[k] >= 70:
                recommendation = f"Over {k}.5"
                break

        return {
            'match_has_data': home_corners['has_data'] or away_corners['has_data'],
            'home': home_corners,
            'away': away_corners,
            'match_overs': match_overs,
            'match_unders': match_unders,
            'recommendation': recommendation
        }

    def get_disciplinary_stats(self):
        def get_stats(matches, team):
            yellow = red = fouls = 0
            valid = 0
            for m in matches:
                if m.home_yellow is not None and m.home_fouls is not None:
                    valid += 1
                    is_home = (m.home_team_id == team.id)
                    yellow += m.home_yellow if is_home else m.away_yellow
                    red += m.home_red if is_home else m.away_red
                    fouls += m.home_fouls if is_home else m.away_fouls
            
            if valid == 0: return {'has_data': False, 'yellow': 0, 'red': 0, 'fouls': 0}
            return {
                'has_data': True,
                'yellow': round(yellow / valid, 1),
                'red': round(red / valid, 2),
                'fouls': round(fouls / valid, 1)
            }
        
        home_stats = get_stats(self.home_last_10, self.home_team)
        away_stats = get_stats(self.away_last_10, self.away_team)
        return {
            'match_has_data': home_stats['has_data'] or away_stats['has_data'],
            'home': home_stats,
            'away': away_stats
        }

    def get_shot_efficiency(self):
        def get_stats(matches, team):
            shots = on_target = goals = 0
            valid = 0
            for m in matches:
                if m.home_shots is not None and m.home_shots_on_target is not None:
                    valid += 1
                    is_home = (m.home_team_id == team.id)
                    s = m.home_shots if is_home else m.away_shots
                    st = m.home_shots_on_target if is_home else m.away_shots_on_target
                    g = m.home_score if is_home else m.away_score
                    shots += s
                    on_target += st
                    goals += g
            
            if valid == 0 or shots == 0: return {'has_data': False, 'accuracy': 0, 'conversion': 0, 'avg_shots': 0}
            return {
                'has_data': True,
                'avg_shots': round(shots / valid, 1),
                'accuracy': int((on_target / shots) * 100),
                'conversion': round(shots / goals, 1) if goals > 0 else 0
            }
        
        home_stats = get_stats(self.home_last_10, self.home_team)
        away_stats = get_stats(self.away_last_10, self.away_team)
        return {
            'match_has_data': home_stats['has_data'] or away_stats['has_data'],
            'home': home_stats,
            'away': away_stats
        }

    def get_value_bet(self):
        # Very basic value bet detector for Match Odds (1 X 2)
        if not self.match.home_team_win_odds:
            return None
            
        general = self.get_general_form()
        home_win_pct = general['home']['win_pct']
        
        # Require at least some history
        if general['home']['total'] < 5:
            return None
            
        # Example logic: if Home win % is high, calculate fair odd
        if home_win_pct > 0:
            fair_odd = 100 / home_win_pct
            offered_odd = self.match.home_team_win_odds
            
            # If offered odd is at least 10% higher than fair odd
            if offered_odd > (fair_odd * 1.1) and home_win_pct >= 50:
                return {
                    'market': 'Home Win (1)',
                    'prob': home_win_pct,
                    'fair_odd': round(fair_odd, 2),
                    'offered_odd': offered_odd,
                    'edge': round(((offered_odd / fair_odd) - 1) * 100, 1)
                }
        return None

    def get_lay_bets(self):
        lays = []
        odds = self.get_match_odds_probs()
        goals = self.get_goal_markets()
        
        # Lay Match Odds
        if odds['home_win'] <= 25:
            lays.append({'market': f"Lay {self.home_team.name}", 'prob': 100 - odds['home_win'], 'reason': f"Home win probability is only {odds['home_win']}%"})
        if odds['away_win'] <= 25:
            lays.append({'market': f"Lay {self.away_team.name}", 'prob': 100 - odds['away_win'], 'reason': f"Away win probability is only {odds['away_win']}%"})
        if odds['draw'] <= 25:
            lays.append({'market': "Lay Draw", 'prob': 100 - odds['draw'], 'reason': f"Draw probability is only {odds['draw']}%"})
            
        # Lay Goals
        if goals['over_25'] <= 35:
            lays.append({'market': "Lay Over 2.5 Goals", 'prob': 100 - goals['over_25'], 'reason': f"Over 2.5 probability is only {goals['over_25']}%"})
        elif goals['over_25'] >= 65:
            lays.append({'market': "Lay Under 2.5 Goals", 'prob': goals['over_25'], 'reason': f"Over 2.5 probability is {goals['over_25']}% (high)"})
            
        # Lay BTTS
        if goals['btts'] <= 35:
            lays.append({'market': "Lay BTTS (Yes)", 'prob': 100 - goals['btts'], 'reason': f"BTTS probability is only {goals['btts']}%"})
            
        # Lay Correct Score
        if goals['over_05'] >= 85:
            lays.append({'market': "Lay Score 0-0", 'prob': goals['over_05'], 'reason': f"Over 0.5 goals probability is {goals['over_05']}%"})
            
        if goals['over_25'] <= 35:
            lays.append({'market': "Lay Any Other Score (4+ goals)", 'prob': 100 - goals['over_25'], 'reason': f"Low probability of a high scoring match"})
            
        # Sort by highest lay success probability
        lays.sort(key=lambda x: x['prob'], reverse=True)
        return lays

    def get_summary_text(self):
        general = self.get_general_form()
        strength = self.get_team_strength()
        goals = self.get_goal_markets()
        
        home = general['home']
        away = general['away']
        
        text = (
            f"{self.home_team.name} has a {home['win_pct']}% win rate playing at home "
            f"(scoring an average of {home['avg_gf']} goals). Their attack is considered {strength['home_attack'].lower()} "
            f"and defense {strength['home_defense'].lower()}. On the other hand, {self.away_team.name} as the away team "
            f"wins {away['win_pct']}% of their matches, with an {strength['away_attack'].lower()} attack. "
            f"Statistically, this matchup has a {goals['over_15']}% chance of hitting Over 1.5 "
            f"and a {goals['btts']}% chance of Both Teams to Score (BTTS)."
        )
        return text

    def generate_full_report(self):
        return {
            'general_form': self.get_general_form(),
            'specific_form': self.get_specific_form(),
            'strength': self.get_team_strength(),
            'goals': self.get_goal_markets(),
            'corners': self.get_corner_markets(),
            'disciplinary': self.get_disciplinary_stats(),
            'efficiency': self.get_shot_efficiency(),
            'odds_probs': self.get_match_odds_probs(),
            'value_bet': self.get_value_bet(),
            'lay_bets': self.get_lay_bets(),
            'summary': self.get_summary_text()
        }
