from django.db.models import Q
from matches.models import Match
from django.utils.translation import gettext_lazy as _

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
            qs = qs.filter(home_team=team).order_by('-date')[:limit]
            return list(qs)
        elif is_away:
            qs = qs.filter(away_team=team).order_by('-date')[:limit]
            return list(qs)
        else:
            home_qs = qs.filter(home_team=team).order_by('-date')[:limit]
            away_qs = qs.filter(away_team=team).order_by('-date')[:limit]
            combined = sorted(list(home_qs) + list(away_qs), key=lambda x: x.date if x.date else x.created_at, reverse=True)[:limit]
            return combined

    def _calc_win_draw_loss(self, matches, team):
        w = d = l = 0
        gf = ga = 0
        total = len(matches)
        if total == 0:
            return {
                'w': 0, 'd': 0, 'l': 0, 
                'gf': 0, 'ga': 0, 
                'avg_gf': 0.0,
                'avg_ga': 0.0,
                'total': 0, 
                'win_pct': 0,
                'loss_pct': 0
            }
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
        # Force makemessages to extract these keys
        _('Strong')
        _('Average')
        _('Weak')
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
        
        def calc_first_to_score(matches, team):
            if not matches: return 0
            count = sum(1 for m in matches if (m.home_team_id == team.id and m.home_score > 0) or (m.away_team_id == team.id and m.away_score > 0))
            return int((count / len(matches)) * 100)
            
        def calc_advanced_match_stats(matches):
            if not matches: return {}
            valid = btts_1h = btts_2h = btts_both = 0
            b1_1_2 = b1_2_3 = b1_2_4 = b2_1_2 = b2_2_3 = b2_2_4 = b_1_2 = b_2_3 = b_2_4 = 0
            for m in matches:
                if m.ht_home_score is not None and m.ht_away_score is not None and m.home_score is not None:
                    valid += 1
                    h1, a1 = m.ht_home_score, m.ht_away_score
                    h2, a2 = m.home_score - h1, m.away_score - a1
                    
                    if h1 > 0 and a1 > 0: btts_1h += 1
                    if h2 > 0 and a2 > 0: btts_2h += 1
                    if (h1 > 0 and a1 > 0) and (h2 > 0 and a2 > 0): btts_both += 1
                    
                    t1, t2, t = h1 + a1, h2 + a2, m.home_score + m.away_score
                    if 1 <= t1 <= 2: b1_1_2 += 1
                    if 2 <= t1 <= 3: b1_2_3 += 1
                    if 2 <= t1 <= 4: b1_2_4 += 1
                    if 1 <= t2 <= 2: b2_1_2 += 1
                    if 2 <= t2 <= 3: b2_2_3 += 1
                    if 2 <= t2 <= 4: b2_2_4 += 1
                    if 1 <= t <= 2: b_1_2 += 1
                    if 2 <= t <= 3: b_2_3 += 1
                    if 2 <= t <= 4: b_2_4 += 1
                    
            if valid == 0: return {}
            return {
                'btts_1h': int((btts_1h / valid) * 100),
                'btts_2h': int((btts_2h / valid) * 100),
                'btts_both': int((btts_both / valid) * 100),
                'bracket_1t_1_2': int((b1_1_2 / valid) * 100),
                'bracket_1t_2_3': int((b1_2_3 / valid) * 100),
                'bracket_1t_2_4': int((b1_2_4 / valid) * 100),
                'bracket_2t_1_2': int((b2_1_2 / valid) * 100),
                'bracket_2t_2_3': int((b2_2_3 / valid) * 100),
                'bracket_2t_2_4': int((b2_2_4 / valid) * 100),
                'bracket_ft_1_2': int((b_1_2 / valid) * 100),
                'bracket_ft_2_3': int((b_2_3 / valid) * 100),
                'bracket_ft_2_4': int((b_2_4 / valid) * 100),
            }
            
        def calc_team_goal_stats(matches, team):
            if not matches: return {}
            valid = cs = wtn = comeback = 0
            for m in matches:
                if m.ht_home_score is not None and m.home_score is not None:
                    valid += 1
                    is_home = (m.home_team_id == team.id)
                    gf = m.home_score if is_home else m.away_score
                    ga = m.away_score if is_home else m.home_score
                    ht_gf = m.ht_home_score if is_home else m.ht_away_score
                    ht_ga = m.ht_away_score if is_home else m.ht_home_score
                    
                    if ga == 0:
                        cs += 1
                        if gf > 0: wtn += 1
                    if ht_gf < ht_ga and gf > ga:
                        comeback += 1
            if valid == 0: return {}
            return {
                'clean_sheet': int((cs / valid) * 100),
                'win_to_nil': int((wtn / valid) * 100),
                'comeback': int((comeback / valid) * 100),
            }

        base_stats = {
            'over_05': calc_over(combined_matches, 0.5),
            'over_15': calc_over(combined_matches, 1.5),
            'over_25': calc_over(combined_matches, 2.5),
            'over_35': calc_over(combined_matches, 3.5),
            'under_35': 100 - calc_over(combined_matches, 3.5),
            'under_45': 100 - calc_over(combined_matches, 4.5),
            'under_55': 100 - calc_over(combined_matches, 5.5),
            'under_65': 100 - calc_over(combined_matches, 6.5),
            'btts': calc_btts(combined_matches),
            'ht_goal': calc_ht_goal(combined_matches),
            'home_first_score': calc_first_to_score(self.home_last_10, self.home_team),
            'away_first_score': calc_first_to_score(self.away_last_10, self.away_team),
            'home_special': calc_team_goal_stats(self.home_last_10, self.home_team),
            'away_special': calc_team_goal_stats(self.away_last_10, self.away_team),
        }
        base_stats.update(calc_advanced_match_stats(combined_matches))
        
        # Mapeamento detalhado para mercados combo
        mapped_matches = []
        for m in combined_matches:
            if m.home_score is None or m.away_score is None:
                continue
            is_home_win = (m.home_team_id == self.home_team.id and m.home_score > m.away_score) or \
                          (m.away_team_id == self.home_team.id and m.away_score > m.home_score)
            is_away_win = (m.home_team_id == self.away_team.id and m.home_score > m.away_score) or \
                          (m.away_team_id == self.away_team.id and m.away_score > m.home_score)
            is_draw = m.home_score == m.away_score
            
            is_home_win_ht = False
            is_away_win_ht = False
            is_draw_ht = False
            if m.ht_home_score is not None and m.ht_away_score is not None:
                is_home_win_ht = (m.home_team_id == self.home_team.id and m.ht_home_score > m.ht_away_score) or \
                                 (m.away_team_id == self.home_team.id and m.ht_away_score > m.ht_home_score)
                is_away_win_ht = (m.home_team_id == self.away_team.id and m.ht_home_score > m.ht_away_score) or \
                                 (m.away_team_id == self.away_team.id and m.ht_away_score > m.ht_home_score)
                is_draw_ht = m.ht_home_score == m.ht_away_score
                
            gf = m.home_score if m.home_team_id == self.home_team.id else m.away_score
            ga = m.away_score if m.home_team_id == self.home_team.id else m.home_score
            ht_gf = m.ht_home_score if m.home_team_id == self.home_team.id else m.ht_away_score
            ht_ga = m.ht_away_score if m.home_team_id == self.home_team.id else m.ht_home_score
            
            mapped_matches.append({
                'home_win': is_home_win,
                'away_win': is_away_win,
                'draw': is_draw,
                'home_win_ht': is_home_win_ht,
                'away_win_ht': is_away_win_ht,
                'draw_ht': is_draw_ht,
                'total_goals': m.home_score + m.away_score,
                'ht_total_goals': (m.ht_home_score + m.ht_away_score) if (m.ht_home_score is not None and m.ht_away_score is not None) else None,
                'btts': m.home_score > 0 and m.away_score > 0,
                'gf': gf,
                'ga': ga,
                'ht_gf': ht_gf,
                'ht_ga': ht_ga
            })

        # Margens de vitória
        h1 = h2 = h3p = dg = dng = a1 = a2 = a3p = 0
        for item in mapped_matches:
            diff = item['gf'] - item['ga']
            if diff > 0:
                if diff == 1: h1 += 1
                elif diff == 2: h2 += 1
                else: h3p += 1
            elif diff < 0:
                abs_diff = abs(diff)
                if abs_diff == 1: a1 += 1
                elif abs_diff == 2: a2 += 1
                else: a3p += 1
            else:
                if item['gf'] > 0: dg += 1
                else: dng += 1
        
        total_mapped = len(mapped_matches) or 1
        base_stats['winning_margins'] = {
            'home_1': int((h1 / total_mapped) * 100),
            'home_2': int((h2 / total_mapped) * 100),
            'home_3plus': int((h3p / total_mapped) * 100),
            'draw_goals': int((dg / total_mapped) * 100),
            'draw_no_goals': int((dng / total_mapped) * 100),
            'away_1': int((a1 / total_mapped) * 100),
            'away_2': int((a2 / total_mapped) * 100),
            'away_3plus': int((a3p / total_mapped) * 100),
        }

        # Double Chance + Faixa de Gols
        dc_brackets = {}
        for combo in ['1X', 'X2', '12']:
            for bracket in ['1-2', '1-3', '2-3', '2-4']:
                count = 0
                for item in mapped_matches:
                    has_dc = False
                    if combo == '1X': has_dc = item['home_win'] or item['draw']
                    elif combo == 'X2': has_dc = item['away_win'] or item['draw']
                    elif combo == '12': has_dc = item['home_win'] or item['away_win']
                    
                    min_g, max_g = map(int, bracket.split('-'))
                    has_bracket = min_g <= item['total_goals'] <= max_g
                    
                    if has_dc and has_bracket:
                        count += 1
                dc_brackets[f"{combo}_{bracket.replace('-', '_')}"] = int((count / total_mapped) * 100)
        base_stats['dc_brackets'] = dc_brackets

        # Double Chance + Under Goals
        # Separate mapping to get correct individual team stats (avoiding artificially halved percentages)
        home_mapped_ind = []
        for m in self.home_last_10:
            if m.home_score is None or m.away_score is None:
                continue
            is_win_or_draw = (m.home_team_id == self.home_team.id and m.home_score >= m.away_score) or \
                             (m.away_team_id == self.home_team.id and m.away_score >= m.home_score)
            home_mapped_ind.append({
                'win_or_draw': is_win_or_draw,
                'win': (m.home_team_id == self.home_team.id and m.home_score > m.away_score) or \
                       (m.away_team_id == self.home_team.id and m.away_score > m.home_score),
                'total_goals': m.home_score + m.away_score,
                'btts': m.home_score > 0 and m.away_score > 0
            })
        total_home_ind = len(home_mapped_ind) or 1

        away_mapped_ind = []
        for m in self.away_last_10:
            if m.home_score is None or m.away_score is None:
                continue
            is_win_or_draw = (m.home_team_id == self.away_team.id and m.home_score >= m.away_score) or \
                             (m.away_team_id == self.away_team.id and m.away_score >= m.home_score)
            away_mapped_ind.append({
                'win_or_draw': is_win_or_draw,
                'win': (m.home_team_id == self.away_team.id and m.home_score > m.away_score) or \
                       (m.away_team_id == self.away_team.id and m.away_score > m.home_score),
                'total_goals': m.home_score + m.away_score,
                'btts': m.home_score > 0 and m.away_score > 0
            })
        total_away_ind = len(away_mapped_ind) or 1

        dc_unders = {}
        for line in [2.5, 3.5, 4.5, 5.5]:
            line_str = str(line).replace('.', '_')
            # 1X under line
            c_1x = sum(1 for x in home_mapped_ind if x['win_or_draw'] and x['total_goals'] < line)
            dc_unders[f"1X_under_{line_str}"] = int((c_1x / total_home_ind) * 100)
            # X2 under line
            c_x2 = sum(1 for x in away_mapped_ind if x['win_or_draw'] and x['total_goals'] < line)
            dc_unders[f"X2_under_{line_str}"] = int((c_x2 / total_away_ind) * 100)
        base_stats['dc_unders'] = dc_unders

        # Double Chance + Over Goals
        dc_overs = {}
        for line in [0.5, 1.5, 2.5, 3.5]:
            line_str = str(line).replace('.', '_')
            # 1X over line
            c_1x = sum(1 for x in home_mapped_ind if x['win_or_draw'] and x['total_goals'] > line)
            dc_overs[f"1X_over_{line_str}"] = int((c_1x / total_home_ind) * 100)
            # X2 over line
            c_x2 = sum(1 for x in away_mapped_ind if x['win_or_draw'] and x['total_goals'] > line)
            dc_overs[f"X2_over_{line_str}"] = int((c_x2 / total_away_ind) * 100)
        base_stats['dc_overs'] = dc_overs

        # Double Chance + BTTS
        dc_btts = {}
        for suffix, btts_val in [('yes', True), ('no', False)]:
            # 1X btts
            c_1x = sum(1 for x in home_mapped_ind if x['win_or_draw'] and x['btts'] == btts_val)
            dc_btts[f"1X_btts_{suffix}"] = int((c_1x / total_home_ind) * 100)
            # X2 btts
            c_x2 = sum(1 for x in away_mapped_ind if x['win_or_draw'] and x['btts'] == btts_val)
            dc_btts[f"X2_btts_{suffix}"] = int((c_x2 / total_away_ind) * 100)
        base_stats['dc_btts'] = dc_btts

        # Winner + BTTS
        base_stats['winner_btts'] = {
            'home_yes': int((sum(1 for item in home_mapped_ind if item['win'] and item['btts']) / total_home_ind) * 100),
            'home_no': int((sum(1 for item in home_mapped_ind if item['win'] and not item['btts']) / total_home_ind) * 100),
            'draw_yes': int((sum(1 for item in mapped_matches if item['draw'] and item['btts']) / total_mapped) * 100),
            'draw_no': int((sum(1 for item in mapped_matches if item['draw'] and not item['btts']) / total_mapped) * 100),
            'away_yes': int((sum(1 for item in away_mapped_ind if item['win'] and item['btts']) / total_away_ind) * 100),
            'away_no': int((sum(1 for item in away_mapped_ind if item['win'] and not item['btts']) / total_away_ind) * 100),
        }

        # Winner + Gols
        base_stats['winner_goals'] = {
            'home_over_15': int((sum(1 for item in mapped_matches if item['home_win'] and item['total_goals'] > 1.5) / total_mapped) * 100),
            'home_under_25': int((sum(1 for item in mapped_matches if item['home_win'] and item['total_goals'] < 2.5) / total_mapped) * 100),
            'home_over_25': int((sum(1 for item in mapped_matches if item['home_win'] and item['total_goals'] > 2.5) / total_mapped) * 100),
            'home_under_35': int((sum(1 for item in mapped_matches if item['home_win'] and item['total_goals'] < 3.5) / total_mapped) * 100),
            
            'draw_over_15': int((sum(1 for item in mapped_matches if item['draw'] and item['total_goals'] > 1.5) / total_mapped) * 100),
            'draw_under_25': int((sum(1 for item in mapped_matches if item['draw'] and item['total_goals'] < 2.5) / total_mapped) * 100),
            'draw_over_25': int((sum(1 for item in mapped_matches if item['draw'] and item['total_goals'] > 2.5) / total_mapped) * 100),
            'draw_under_35': int((sum(1 for item in mapped_matches if item['draw'] and item['total_goals'] < 3.5) / total_mapped) * 100),
            
            'away_over_15': int((sum(1 for item in mapped_matches if item['away_win'] and item['total_goals'] > 1.5) / total_mapped) * 100),
            'away_under_25': int((sum(1 for item in mapped_matches if item['away_win'] and item['total_goals'] < 2.5) / total_mapped) * 100),
            'away_over_25': int((sum(1 for item in mapped_matches if item['away_win'] and item['total_goals'] > 2.5) / total_mapped) * 100),
            'away_under_35': int((sum(1 for item in mapped_matches if item['away_win'] and item['total_goals'] < 3.5) / total_mapped) * 100),
        }

        # Goals + BTTS
        base_stats['goals_btts'] = {
            'over_25_yes': int((sum(1 for item in mapped_matches if item['total_goals'] > 2.5 and item['btts']) / total_mapped) * 100),
            'over_25_no': int((sum(1 for item in mapped_matches if item['total_goals'] > 2.5 and not item['btts']) / total_mapped) * 100),
            'under_25_yes': int((sum(1 for item in mapped_matches if item['total_goals'] < 2.5 and item['btts']) / total_mapped) * 100),
            'under_25_no': int((sum(1 for item in mapped_matches if item['total_goals'] < 2.5 and not item['btts']) / total_mapped) * 100),
        }

        # HT/FT
        ht_ft_counts = {f"{ht}_{ft}": 0 for ht in ['1', 'X', '2'] for ft in ['1', 'X', '2']}
        valid_ht_ft = 0
        for item in mapped_matches:
            if item['ht_total_goals'] is not None:
                valid_ht_ft += 1
                ht_res = '1' if item['home_win_ht'] else ('2' if item['away_win_ht'] else 'X')
                ft_res = '1' if item['home_win'] else ('2' if item['away_win'] else 'X')
                ht_ft_counts[f"{ht_res}_{ft_res}"] += 1
        div_ht_ft = valid_ht_ft or 1
        base_stats['ht_ft'] = {k: int((v / div_ht_ft) * 100) for k, v in ht_ft_counts.items()}

        # Half with most goals
        most_goals_counts = {'1t': 0, '2t': 0, 'igual': 0}
        valid_most = 0
        for item in mapped_matches:
            if item['ht_total_goals'] is not None:
                valid_most += 1
                t1 = item['ht_total_goals']
                t2 = item['total_goals'] - t1
                if t1 > t2: most_goals_counts['1t'] += 1
                elif t2 > t1: most_goals_counts['2t'] += 1
                else: most_goals_counts['igual'] += 1
        div_most = valid_most or 1
        base_stats['half_most_goals'] = {k: int((v / div_most) * 100) for k, v in most_goals_counts.items()}

        # Team scoring in halves
        h_1t = h_2t = h_both = h_one = 0
        a_1t = a_2t = a_both = a_one = 0
        valid_sh = 0
        for item in mapped_matches:
            if item['ht_total_goals'] is not None:
                valid_sh += 1
                scored_1t_h = item['ht_gf'] is not None and item['ht_gf'] > 0
                scored_2t_h = (item['gf'] is not None and item['ht_gf'] is not None) and (item['gf'] - item['ht_gf'] > 0)
                if scored_1t_h: h_1t += 1
                if scored_2t_h: h_2t += 1
                if scored_1t_h and scored_2t_h: h_both += 1
                if scored_1t_h or scored_2t_h: h_one += 1
                
                scored_1t_a = item['ht_ga'] is not None and item['ht_ga'] > 0
                scored_2t_a = (item['ga'] is not None and item['ht_ga'] is not None) and (item['ga'] - item['ht_ga'] > 0)
                if scored_1t_a: a_1t += 1
                if scored_2t_a: a_2t += 1
                if scored_1t_a and scored_2t_a: a_both += 1
                if scored_1t_a or scored_2t_a: a_one += 1
        div_sh = valid_sh or 1
        base_stats['team_scoring_halves'] = {
            'home_1t': int((h_1t / div_sh) * 100),
            'home_2t': int((h_2t / div_sh) * 100),
            'home_both': int((h_both / div_sh) * 100),
            'home_one': int((h_one / div_sh) * 100),
            
            'away_1t': int((a_1t / div_sh) * 100),
            'away_2t': int((a_2t / div_sh) * 100),
            'away_both': int((a_both / div_sh) * 100),
            'away_one': int((a_one / div_sh) * 100),
        }

        # Draw No Bet
        total_non_draws = sum(1 for item in mapped_matches if not item['draw']) or 1
        base_stats['dnb'] = {
            'home': int((sum(1 for item in mapped_matches if item['home_win']) / total_non_draws) * 100),
            'away': int((sum(1 for item in mapped_matches if item['away_win']) / total_non_draws) * 100)
        }
        if base_stats['dnb']['home'] + base_stats['dnb']['away'] > 0:
            s = base_stats['dnb']['home'] + base_stats['dnb']['away']
            base_stats['dnb']['home'] = int((base_stats['dnb']['home'] / s) * 100)
            base_stats['dnb']['away'] = 100 - base_stats['dnb']['home']

        # Handicaps
        base_stats['handicaps'] = {
            'home_minus_1_5': int((sum(1 for item in mapped_matches if item['gf'] - item['ga'] >= 2) / total_mapped) * 100),
            'home_minus_1_0': int((sum(1 for item in mapped_matches if item['gf'] - item['ga'] >= 2) / total_mapped) * 100),
            'home_minus_0_5': int((sum(1 for item in mapped_matches if item['gf'] - item['ga'] >= 1) / total_mapped) * 100),
            'away_plus_1_5': int((sum(1 for item in mapped_matches if item['ga'] - item['gf'] >= -1) / total_mapped) * 100),
            'away_plus_1_0': int((sum(1 for item in mapped_matches if item['ga'] - item['gf'] >= -1) / total_mapped) * 100),
            'away_plus_0_5': int((sum(1 for item in mapped_matches if item['ga'] - item['gf'] >= 0) / total_mapped) * 100),
            
            'home_plus_1_5': int((sum(1 for item in mapped_matches if item['gf'] - item['ga'] >= -1) / total_mapped) * 100),
            'home_plus_1_0': int((sum(1 for item in mapped_matches if item['gf'] - item['ga'] >= -1) / total_mapped) * 100),
            'home_plus_0_5': int((sum(1 for item in mapped_matches if item['gf'] - item['ga'] >= 0) / total_mapped) * 100),
            'away_minus_1_5': int((sum(1 for item in mapped_matches if item['ga'] - item['gf'] >= 2) / total_mapped) * 100),
            'away_minus_1_0': int((sum(1 for item in mapped_matches if item['ga'] - item['gf'] >= 2) / total_mapped) * 100),
            'away_minus_0_5': int((sum(1 for item in mapped_matches if item['ga'] - item['gf'] >= 1) / total_mapped) * 100),
        }

        # 1T Winner
        t1_h = t1_a = t1_d = 0
        valid_t1_winner = 0
        for item in mapped_matches:
            if item['ht_total_goals'] is not None:
                valid_t1_winner += 1
                if item['home_win_ht']: t1_h += 1
                elif item['away_win_ht']: t1_a += 1
                else: t1_d += 1
        div_t1 = valid_t1_winner or 1
        base_stats['ht_winner'] = {
            'home': int((t1_h / div_t1) * 100),
            'draw': int((t1_d / div_t1) * 100),
            'away': int((t1_a / div_t1) * 100),
        }

        return base_stats

    def _get_h2h_matches(self, limit=10):
        """Busca confrontos diretos entre os dois times."""
        qs = Match.objects.filter(
            home_score__isnull=False,
            away_score__isnull=False
        )
        if self.match.date:
            qs = qs.filter(date__lt=self.match.date)
        
        h2h = qs.filter(
            Q(home_team=self.home_team, away_team=self.away_team) |
            Q(home_team=self.away_team, away_team=self.home_team)
        ).order_by('-date')[:limit]
        return list(h2h)

    def _odds_to_probs(self):
        """Converte odds decimais reais em probabilidades implícitas normalizadas."""
        m = self.match
        if not m.home_team_win_odds or not m.draw_odds or not m.away_team_win_odds:
            return None
        
        # Probabilidades implícitas brutas (incluem margem da casa)
        raw_home = 1 / m.home_team_win_odds
        raw_draw = 1 / m.draw_odds
        raw_away = 1 / m.away_team_win_odds
        total = raw_home + raw_draw + raw_away
        
        # Normaliza para somar 100%
        return {
            'home': int((raw_home / total) * 100),
            'draw': int((raw_draw / total) * 100),
            'away': int((raw_away / total) * 100),
        }

    def get_match_odds_probs(self):
        """
        Modelo de previsão multi-fator com pesos dinâmicos.
        
        Fatores utilizados:
        1. Forma geral (últimos 10 jogos de cada time) — peso 15%
        2. Forma específica (casa/fora) — peso 25%
        3. Força de ataque/defesa (modelo xG simplificado) — peso 20%
        4. Confronto direto (H2H) — peso 15% (se disponível)
        5. Odds reais das casas de apostas — peso 25% (se disponível)
        
        Quando um fator não está disponível, seu peso é redistribuído
        proporcionalmente entre os demais.
        """
        home_stats = self._calc_win_draw_loss(self.home_last_10_home, self.home_team)
        away_stats = self._calc_win_draw_loss(self.away_last_10_away, self.away_team)
        home_general = self._calc_win_draw_loss(self.home_last_10, self.home_team)
        away_general = self._calc_win_draw_loss(self.away_last_10, self.away_team)
        
        # ═══════════════════════════════════════════════════════
        # FATOR 1: Forma Geral (últimos 10 jogos)
        # ═══════════════════════════════════════════════════════
        f1_home = home_general['win_pct']
        f1_away = away_general['win_pct']
        f1_draw = 100 - f1_home - f1_away
        if f1_draw < 0:
            f1_draw = 10
        total_f1 = f1_home + f1_away + f1_draw
        f1_home = (f1_home / total_f1) * 100
        f1_away = (f1_away / total_f1) * 100
        f1_draw = (f1_draw / total_f1) * 100
        
        # ═══════════════════════════════════════════════════════
        # FATOR 2: Forma Específica (mandante em casa / visitante fora)
        # ═══════════════════════════════════════════════════════
        f2_home = home_stats['win_pct']
        f2_away = away_stats['win_pct']
        f2_draw = 100 - f2_home - f2_away
        if f2_draw < 0:
            f2_draw = 10
        total_f2 = f2_home + f2_away + f2_draw
        f2_home = (f2_home / total_f2) * 100
        f2_away = (f2_away / total_f2) * 100
        f2_draw = (f2_draw / total_f2) * 100
        
        # ═══════════════════════════════════════════════════════
        # FATOR 3: Força Ataque/Defesa (modelo xG simplificado)
        # Compara o ataque do mandante com a defesa do visitante e vice-versa
        # ═══════════════════════════════════════════════════════
        home_attack = home_general['avg_gf']   # Gols marcados por jogo
        home_defense = home_general['avg_ga']   # Gols sofridos por jogo
        away_attack = away_general['avg_gf']
        away_defense = away_general['avg_ga']
        
        # Expected goals: ataque do time vs defesa do oponente
        # Ajuste com fator casa (+10% para mandante)
        xg_home = ((home_attack + away_defense) / 2) * 1.10
        xg_away = ((away_attack + home_defense) / 2) * 0.90
        
        # Converte xG em probabilidades via Poisson simplificado
        import math
        def poisson_prob(xg, k):
            """P(X=k) para distribuição de Poisson."""
            return (math.exp(-xg) * (xg ** k)) / math.factorial(k)
        
        # Calcula probabilidades de resultado via soma de Poisson
        p_home_win = 0
        p_draw = 0
        p_away_win = 0
        max_goals = 7  # Calcula até 7 gols por time
        
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                prob = poisson_prob(max(xg_home, 0.1), h) * poisson_prob(max(xg_away, 0.1), a)
                if h > a:
                    p_home_win += prob
                elif h == a:
                    p_draw += prob
                else:
                    p_away_win += prob
        
        total_poisson = p_home_win + p_draw + p_away_win
        f3_home = (p_home_win / total_poisson) * 100
        f3_draw = (p_draw / total_poisson) * 100
        f3_away = (p_away_win / total_poisson) * 100
        
        # ═══════════════════════════════════════════════════════
        # FATOR 4: Confronto Direto (H2H)
        # ═══════════════════════════════════════════════════════
        h2h_matches = self._get_h2h_matches(limit=10)
        has_h2h = len(h2h_matches) >= 3  # Mínimo 3 confrontos para relevância
        
        if has_h2h:
            h2h_home_wins = 0
            h2h_draws = 0
            h2h_away_wins = 0
            for m in h2h_matches:
                if m.home_team_id == self.home_team.id:
                    if m.home_score > m.away_score:
                        h2h_home_wins += 1
                    elif m.home_score == m.away_score:
                        h2h_draws += 1
                    else:
                        h2h_away_wins += 1
                else:
                    # Jogo invertido (nosso mandante jogou como visitante)
                    if m.away_score > m.home_score:
                        h2h_home_wins += 1
                    elif m.home_score == m.away_score:
                        h2h_draws += 1
                    else:
                        h2h_away_wins += 1
            
            h2h_total = len(h2h_matches)
            f4_home = (h2h_home_wins / h2h_total) * 100
            f4_draw = (h2h_draws / h2h_total) * 100
            f4_away = (h2h_away_wins / h2h_total) * 100
        else:
            f4_home = f4_draw = f4_away = 0
        
        # ═══════════════════════════════════════════════════════
        # FATOR 5: Odds Reais das Casas de Apostas
        # ═══════════════════════════════════════════════════════
        odds_probs = self._odds_to_probs()
        has_odds = odds_probs is not None
        
        if has_odds:
            f5_home = odds_probs['home']
            f5_draw = odds_probs['draw']
            f5_away = odds_probs['away']
        else:
            f5_home = f5_draw = f5_away = 0
        
        # ═══════════════════════════════════════════════════════
        # COMBINAÇÃO COM PESOS DINÂMICOS
        # ═══════════════════════════════════════════════════════
        # Pesos base
        weights = {
            'general_form': 15,
            'specific_form': 25,
            'strength_xg': 20,
            'h2h': 15 if has_h2h else 0,
            'odds': 25 if has_odds else 0,
        }
        
        # Redistribui pesos ausentes proporcionalmente
        active_weight = sum(weights.values())
        if active_weight < 100:
            scale = 100 / active_weight
            weights = {k: v * scale for k, v in weights.items()}
        
        # Calcula probabilidade final ponderada
        prob_home = (
            f1_home * weights['general_form'] +
            f2_home * weights['specific_form'] +
            f3_home * weights['strength_xg'] +
            f4_home * weights['h2h'] +
            f5_home * weights['odds']
        ) / 100
        
        prob_draw = (
            f1_draw * weights['general_form'] +
            f2_draw * weights['specific_form'] +
            f3_draw * weights['strength_xg'] +
            f4_draw * weights['h2h'] +
            f5_draw * weights['odds']
        ) / 100
        
        prob_away = (
            f1_away * weights['general_form'] +
            f2_away * weights['specific_form'] +
            f3_away * weights['strength_xg'] +
            f4_away * weights['h2h'] +
            f5_away * weights['odds']
        ) / 100
        
        # Normaliza para somar exatamente 100
        total = prob_home + prob_draw + prob_away
        prob_home = int(round((prob_home / total) * 100))
        prob_away = int(round((prob_away / total) * 100))
        prob_draw = 100 - prob_home - prob_away  # Garante soma = 100
        
        # Garante que nenhuma prob fique negativa
        if prob_draw < 0:
            prob_draw = 0
            total2 = prob_home + prob_away
            prob_home = int(round((prob_home / total2) * 100))
            prob_away = 100 - prob_home
        
        # ═══════════════════════════════════════════════════════
        # DETERMINAÇÃO DO PALPITE (BEST BET) E DUPLA CHANCE
        # ═══════════════════════════════════════════════════════
        max_prob = max(prob_home, prob_draw, prob_away)
        if max_prob == prob_home:
            best_bet = "1"
            best_bet_prob = prob_home
        elif max_prob == prob_away:
            best_bet = "2"
            best_bet_prob = prob_away
        else:
            best_bet = "X"
            best_bet_prob = prob_draw

        # Dupla Chance consistente com o palpite principal
        if best_bet == "1":
            if prob_draw >= prob_away:
                double_bet = "1X"
                double_bet_prob = prob_home + prob_draw
            else:
                double_bet = "12"
                double_bet_prob = prob_home + prob_away
        elif best_bet == "2":
            if prob_draw >= prob_home:
                double_bet = "X2"
                double_bet_prob = prob_away + prob_draw
            else:
                double_bet = "12"
                double_bet_prob = prob_home + prob_away
        else:
            if prob_home >= prob_away:
                double_bet = "1X"
                double_bet_prob = prob_home + prob_draw
            else:
                double_bet = "X2"
                double_bet_prob = prob_away + prob_draw

        return {
            'home_win': prob_home,
            'draw': prob_draw,
            'away_win': prob_away,
            'double_home': prob_home + prob_draw,
            'double_away': prob_away + prob_draw,
            'best_bet': best_bet,
            'best_bet_prob': best_bet_prob,
            'double_bet': double_bet,
            'double_bet_prob': double_bet_prob,
            'has_odds': has_odds,
            'has_h2h': has_h2h,
            'factors_used': sum(1 for v in weights.values() if v > 0),
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
                    
                    scored += (team_c or 0)
                    conceded += (opp_c or 0)
                    total_c = (team_c or 0) + (opp_c or 0)
                    
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
        recommendation = _("No clear suggestion")
        for k in sorted(match_overs.keys(), reverse=True):
            if match_overs[k] >= 70:
                recommendation = _("Over %(val)s.5") % {'val': k}
                break
                
        # Projections for Handicap, Winner
        combined = list(self.home_last_10) + list(self.away_last_10)
        valid_c = 0
        home_win_c = away_win_c = draw_c = 0
        hc_home_minus_1_5 = hc_away_plus_1_5 = 0
        
        for m in combined:
            if m.home_corners is not None and m.away_corners is not None:
                valid_c += 1
                is_home = (m.home_team_id == self.home_team.id)
                t_corners = m.home_corners if is_home else m.away_corners
                o_corners = m.away_corners if is_home else m.home_corners
                if t_corners > o_corners: home_win_c += 1
                elif o_corners > t_corners: away_win_c += 1
                else: draw_c += 1
                
                if t_corners - o_corners >= 2: hc_home_minus_1_5 += 1
                if o_corners - t_corners >= -1: hc_away_plus_1_5 += 1
                
        div_c = valid_c or 1
        
        return {
            'match_has_data': home_corners['has_data'] or away_corners['has_data'],
            'home': home_corners,
            'away': away_corners,
            'match_overs': match_overs,
            'match_unders': match_unders,
            'recommendation': recommendation,
            'winner_corners': {
                'home': int((home_win_c / div_c) * 100),
                'away': int((away_win_c / div_c) * 100),
                'draw': int((draw_c / div_c) * 100)
            },
            'handicaps': {
                'home_minus_1_5': int((hc_home_minus_1_5 / div_c) * 100),
                'away_plus_1_5': int((hc_away_plus_1_5 / div_c) * 100)
            }
        }

    def get_disciplinary_stats(self):
        def get_stats(matches, team):
            yellow = red = fouls = 0
            valid = 0
            for m in matches:
                # Check for basic disciplinary data (yellows)
                if m.home_yellow is not None or m.away_yellow is not None:
                    valid += 1
                    is_home = (m.home_team_id == team.id)
                    yellow += (m.home_yellow or 0) if is_home else (m.away_yellow or 0)
                    red += (m.home_red or 0) if is_home else (m.away_red or 0)
                    fouls += (m.home_fouls or 0) if is_home else (m.away_fouls or 0)
            
            if valid == 0: return {'has_data': False, 'yellow': 0, 'red': 0, 'fouls': 0}
            return {
                'has_data': True,
                'yellow': round(yellow / valid, 1),
                'red': round(red / valid, 2),
                'fouls': round(fouls / valid, 1)
            }
        
        home_stats = get_stats(self.home_last_10, self.home_team)
        away_stats = get_stats(self.away_last_10, self.away_team)
        
        # Calculate O/U cards and card winners
        combined = list(self.home_last_10) + list(self.away_last_10)
        valid_cards = 0
        cards_totals = {3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        home_win_cards = away_win_cards = draw_cards = 0
        hc_home_minus_0_5 = hc_away_plus_0_5 = 0
        
        for m in combined:
            if m.home_yellow is not None and m.away_yellow is not None:
                valid_cards += 1
                is_home = (m.home_team_id == self.home_team.id)
                t_cards = (m.home_yellow or 0) + (m.home_red or 0) * 2 if is_home else (m.away_yellow or 0) + (m.away_red or 0) * 2
                o_cards = (m.away_yellow or 0) + (m.away_red or 0) * 2 if is_home else (m.home_yellow or 0) + (m.home_red or 0) * 2
                tot = t_cards + o_cards
                
                for k in cards_totals.keys():
                    if tot > (k + 0.5): cards_totals[k] += 1
                    
                if t_cards > o_cards: home_win_cards += 1
                elif o_cards > t_cards: away_win_cards += 1
                else: draw_cards += 1
                
                if t_cards - o_cards >= 1: hc_home_minus_0_5 += 1
                if o_cards - t_cards >= 0: hc_away_plus_0_5 += 1
                
        div_cards = valid_cards or 1
        
        return {
            'match_has_data': home_stats['has_data'] or away_stats['has_data'],
            'home': home_stats,
            'away': away_stats,
            'cards_totals_overs': {k: int((v / div_cards) * 100) for k, v in cards_totals.items()},
            'winner_cards': {
                'home': int((home_win_cards / div_cards) * 100),
                'away': int((away_win_cards / div_cards) * 100),
                'draw': int((draw_cards / div_cards) * 100)
            },
            'handicaps': {
                'home_minus_0_5': int((hc_home_minus_0_5 / div_cards) * 100),
                'away_plus_0_5': int((hc_away_plus_0_5 / div_cards) * 100)
            }
        }

    def get_shot_efficiency(self):
        def get_stats(matches, team):
            shots = on_target = goals = 0
            valid = 0
            for m in matches:
                if m.home_shots is not None and m.home_shots_on_target is not None:
                    valid += 1
                    is_home = (m.home_team_id == team.id)
                    s = (m.home_shots or 0) if is_home else (m.away_shots or 0)
                    st = (m.home_shots_on_target or 0) if is_home else (m.away_shots_on_target or 0)
                    g = (m.home_score or 0) if is_home else (m.away_score or 0)
                    shots += s
                    on_target += st
                    goals += g
            
            if valid == 0 or shots == 0: return {'has_data': False, 'accuracy': 0, 'conversion': 0, 'avg_shots': 0, 'avg_on_target': 0}
            return {
                'has_data': True,
                'avg_shots': round(shots / valid, 1),
                'avg_on_target': round(on_target / valid, 1),
                'accuracy': int((on_target / shots) * 100),
                'conversion': round(shots / goals, 1) if goals > 0 else 0
            }
        
        home_stats = get_stats(self.home_last_10, self.home_team)
        away_stats = get_stats(self.away_last_10, self.away_team)
        
        # We blend general form of both teams to calculate match O/U lines
        combined = list(self.home_last_10) + list(self.away_last_10)
        
        valid_match_shots = 0
        shots_totals = {18: 0, 20: 0, 22: 0, 24: 0, 26: 0}
        shots_on_target = {6: 0, 7: 0, 8: 0, 9: 0, 10: 0}
        
        home_win_shots = away_win_shots = draw_shots = 0
        home_win_ot = away_win_ot = draw_ot = 0
        
        home_over_10_5 = home_over_12_5 = home_over_14_5 = 0
        away_over_8_5 = away_over_10_5 = away_over_12_5 = 0
        
        home_ot_over_3_5 = home_ot_over_4_5 = home_ot_over_5_5 = 0
        away_ot_over_2_5 = away_ot_over_3_5 = away_ot_over_4_5 = 0
        
        for m in combined:
            if m.home_shots is not None and m.away_shots is not None and m.home_shots_on_target is not None and m.away_shots_on_target is not None:
                valid_match_shots += 1
                is_home = (m.home_team_id == self.home_team.id)
                t_shots = m.home_shots if is_home else m.away_shots
                o_shots = m.away_shots if is_home else m.home_shots
                t_ot = m.home_shots_on_target if is_home else m.away_shots_on_target
                o_ot = m.away_shots_on_target if is_home else m.home_shots_on_target
                
                tot_s = t_shots + o_shots
                tot_ot = t_ot + o_ot
                
                for k in shots_totals.keys():
                    if tot_s > (k + 0.5): shots_totals[k] += 1
                for k in shots_on_target.keys():
                    if tot_ot > (k + 0.5): shots_on_target[k] += 1
                    
                if t_shots > o_shots: home_win_shots += 1
                elif o_shots > t_shots: away_win_shots += 1
                else: draw_shots += 1
                
                if t_ot > o_ot: home_win_ot += 1
                elif o_ot > t_ot: away_win_ot += 1
                else: draw_ot += 1
                
                if t_shots > 10.5: home_over_10_5 += 1
                if t_shots > 12.5: home_over_12_5 += 1
                if t_shots > 14.5: home_over_14_5 += 1
                
                if o_shots > 8.5: away_over_8_5 += 1
                if o_shots > 10.5: away_over_10_5 += 1
                if o_shots > 12.5: away_over_12_5 += 1
                
                if t_ot > 3.5: home_ot_over_3_5 += 1
                if t_ot > 4.5: home_ot_over_4_5 += 1
                if t_ot > 5.5: home_ot_over_5_5 += 1
                
                if o_ot > 2.5: away_ot_over_2_5 += 1
                if o_ot > 3.5: away_ot_over_3_5 += 1
                if o_ot > 4.5: away_ot_over_4_5 += 1

        div = valid_match_shots or 1
        return {
            'match_has_data': home_stats['has_data'] or away_stats['has_data'],
            'home': home_stats,
            'away': away_stats,
            'shots_totals_overs': {k: int((v / div) * 100) for k, v in shots_totals.items()},
            'shots_on_target_overs': {k: int((v / div) * 100) for k, v in shots_on_target.items()},
            'winner_shots': {
                'home': int((home_win_shots / div) * 100),
                'away': int((away_win_shots / div) * 100),
                'draw': int((draw_shots / div) * 100)
            },
            'winner_shots_ot': {
                'home': int((home_win_ot / div) * 100),
                'away': int((away_win_ot / div) * 100),
                'draw': int((draw_ot / div) * 100)
            },
            'home_shots_overs': {
                '10_5': int((home_over_10_5 / div) * 100),
                '12_5': int((home_over_12_5 / div) * 100),
                '14_5': int((home_over_14_5 / div) * 100)
            },
            'away_shots_overs': {
                '8_5': int((away_over_8_5 / div) * 100),
                '10_5': int((away_over_10_5 / div) * 100),
                '12_5': int((away_over_12_5 / div) * 100)
            },
            'home_ot_overs': {
                '3_5': int((home_ot_over_3_5 / div) * 100),
                '4_5': int((home_ot_over_4_5 / div) * 100),
                '5_5': int((home_ot_over_5_5 / div) * 100)
            },
            'away_ot_overs': {
                '2_5': int((away_ot_over_2_5 / div) * 100),
                '3_5': int((away_ot_over_3_5 / div) * 100),
                '4_5': int((away_ot_over_4_5 / div) * 100)
            }
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
            lays.append({'market': _("Lay %(team)s") % {'team': self.home_team.name}, 'prob': 100 - odds['home_win'], 'reason': _("Home win probability is only %(prob)s%%") % {'prob': odds['home_win']}})
        if odds['away_win'] <= 25:
            lays.append({'market': _("Lay %(team)s") % {'team': self.away_team.name}, 'prob': 100 - odds['away_win'], 'reason': _("Away win probability is only %(prob)s%%") % {'prob': odds['away_win']}})
        if odds['draw'] <= 25:
            lays.append({'market': _("Lay Draw"), 'prob': 100 - odds['draw'], 'reason': _("Draw probability is only %(prob)s%%") % {'prob': odds['draw']}})
            
        # Lay Goals
        if goals['over_25'] <= 35:
            lays.append({'market': _("Lay Over 2.5 Goals"), 'prob': 100 - goals['over_25'], 'reason': _("Over 2.5 probability is only %(prob)s%%") % {'prob': goals['over_25']}})
        elif goals['over_25'] >= 65:
            lays.append({'market': _("Lay Under 2.5 Goals"), 'prob': goals['over_25'], 'reason': _("Over 2.5 probability is %(prob)s%% (high)") % {'prob': goals['over_25']}})
            
        # Lay BTTS
        if goals['btts'] <= 35:
            lays.append({'market': _("Lay BTTS (Yes)"), 'prob': 100 - goals['btts'], 'reason': _("BTTS probability is only %(prob)s%%") % {'prob': goals['btts']}})
            
        # Lay Correct Score
        if goals['over_05'] >= 85:
            lays.append({'market': _("Lay Score 0-0"), 'prob': goals['over_05'], 'reason': _("Over 0.5 goals probability is %(prob)s%%") % {'prob': goals['over_05']}})
            
        if goals['over_25'] <= 35:
            lays.append({'market': _("Lay Any Other Score (4+ goals)"), 'prob': 100 - goals['over_25'], 'reason': _("Low probability of a high scoring match")})
            
        # Sort by highest lay success probability
        lays.sort(key=lambda x: x['prob'], reverse=True)
        return lays

    def get_summary_text(self):
        general = self.get_general_form()
        strength = self.get_team_strength()
        goals = self.get_goal_markets()
        
        home = general['home']
        away = general['away']
        
        # We need to map strengths to translated versions
        # Using string replacement so it can be picked up by makemessages properly
        
        text = _(
            "%(home_team)s has a %(win_pct)s%% win rate playing at home "
            "(scoring an average of %(avg_gf)s goals). Their attack is considered %(home_atk)s "
            "and defense %(home_def)s. On the other hand, %(away_team)s as the away team "
            "wins %(away_win_pct)s%% of their matches, with an %(away_atk)s attack. "
            "Statistically, this matchup has a %(over_15)s%% chance of hitting Over 1.5 "
            "and a %(btts)s%% chance of Both Teams to Score (BTTS)."
        ) % {
            'home_team': self.home_team.name,
            'win_pct': home['win_pct'],
            'avg_gf': home['avg_gf'],
            'home_atk': _(strength['home_attack']).lower(),
            'home_def': _(strength['home_defense']).lower(),
            'away_team': self.away_team.name,
            'away_win_pct': away['win_pct'],
            'away_atk': _(strength['away_attack']).lower(),
            'over_15': goals['over_15'],
            'btts': goals['btts']
        }
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
