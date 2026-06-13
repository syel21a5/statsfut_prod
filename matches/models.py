from django.db import models
from django.utils.text import slugify
from django.core.cache import cache

class League(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    division = models.IntegerField(default=1, help_text="Nível da liga: 1=Primeira Divisão, 2=Segunda, etc.")
    soccerstats_slug = models.CharField(
        max_length=100, blank=True, null=True, unique=True,
        help_text="Slug único no SoccerStats.com (ex: 'england', 'denmark'). Usado para evitar mistura entre divisões."
    )
    api_id = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="ID da Liga na API")

    def __str__(self):
        return f"{self.name} ({self.country}) - Div {self.division}"

class Team(models.Model):
    name = models.CharField(max_length=100)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='teams')
    api_id = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="ID do Time na API")

    def get_stats(self, market="over25"):
        cache_key = f"team_stats_{self.id}_{market}"
        cached_val = cache.get(cache_key)
        if cached_val is not None:
            return cached_val

        # Busca indexada otimizada (sem operador OR lento)
        home_matches = list(Match.objects.filter(
            home_team=self,
            home_score__isnull=False,
            away_score__isnull=False
        ).order_by('-date')[:10])
        
        away_matches = list(Match.objects.filter(
            away_team=self,
            home_score__isnull=False,
            away_score__isnull=False
        ).order_by('-date')[:10])
        
        # Junta e ordena no Python de forma ultrarrápida
        matches = sorted(home_matches + away_matches, key=lambda m: m.date, reverse=True)[:10]
        
        if not matches:
            val = 0
        else:
            count = 0
            for m in matches:
                total = (m.home_score or 0) + (m.away_score or 0)
                if market == "over25" and total > 2.5:
                    count += 1
                elif market == "under15" and total < 1.5:
                    count += 1
            val = int((count / len(matches)) * 100)
            
        # Salva em cache por 6 horas
        cache.set(cache_key, val, 3600 * 6)
        return val

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'league'], name='unique_team_name_per_league')
        ]

class Match(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='matches')
    season = models.ForeignKey('Season', on_delete=models.CASCADE, related_name='matches', null=True)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    date = models.DateTimeField(null=True, blank=True, db_index=True)
    round_name = models.CharField(max_length=150, blank=True, null=True)
    status = models.CharField(max_length=20, default="Scheduled", db_index=True)
    api_id = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text="ID da Fixture na API")
    elapsed_time = models.IntegerField(null=True, blank=True)

    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    ht_home_score = models.IntegerField(null=True, blank=True)
    ht_away_score = models.IntegerField(null=True, blank=True)
    
    # Odds Fields
    home_team_win_odds = models.FloatField(null=True, blank=True)
    draw_odds = models.FloatField(null=True, blank=True)
    away_team_win_odds = models.FloatField(null=True, blank=True)
    
    btts_yes_odds = models.FloatField(null=True, blank=True)
    btts_no_odds = models.FloatField(null=True, blank=True)
    over_15_odds = models.FloatField(null=True, blank=True)
    over_25_odds = models.FloatField(null=True, blank=True)
    over_35_odds = models.FloatField(null=True, blank=True)
    under_25_odds = models.FloatField(null=True, blank=True)
    under_35_odds = models.FloatField(null=True, blank=True)
    under_45_odds = models.FloatField(null=True, blank=True)
    over_45_odds = models.FloatField(null=True, blank=True)
    over_55_odds = models.FloatField(null=True, blank=True)
    under_55_odds = models.FloatField(null=True, blank=True)
    ht_goal_odds = models.FloatField(null=True, blank=True)
    
    # Dupla Chance
    dc_1x_odds = models.FloatField(null=True, blank=True)
    dc_x2_odds = models.FloatField(null=True, blank=True)
    
    # Dupla Chance & Over
    dc_1x_over_15_odds = models.FloatField(null=True, blank=True)
    dc_1x_over_25_odds = models.FloatField(null=True, blank=True)
    dc_1x_over_35_odds = models.FloatField(null=True, blank=True)
    dc_x2_over_15_odds = models.FloatField(null=True, blank=True)
    dc_x2_over_25_odds = models.FloatField(null=True, blank=True)
    dc_x2_over_35_odds = models.FloatField(null=True, blank=True)
    
    # Dupla Chance & Ambas Marcam
    dc_1x_btts_yes_odds = models.FloatField(null=True, blank=True)
    dc_1x_btts_no_odds = models.FloatField(null=True, blank=True)
    dc_x2_btts_yes_odds = models.FloatField(null=True, blank=True)
    dc_x2_btts_no_odds = models.FloatField(null=True, blank=True)
    
    # Especiais
    dnb_home_odds = models.FloatField(null=True, blank=True)
    dnb_away_odds = models.FloatField(null=True, blank=True)
    clean_sheet_home_odds = models.FloatField(null=True, blank=True)
    clean_sheet_away_odds = models.FloatField(null=True, blank=True)
    
    # Escanteios
    corners_over_65_odds = models.FloatField(null=True, blank=True)
    corners_over_75_odds = models.FloatField(null=True, blank=True)
    corners_over_85_odds = models.FloatField(null=True, blank=True)
    corners_over_95_odds = models.FloatField(null=True, blank=True)
    corners_over_105_odds = models.FloatField(null=True, blank=True)
    corners_over_115_odds = models.FloatField(null=True, blank=True)
    corners_home_win_odds = models.FloatField(null=True, blank=True)
    corners_draw_odds = models.FloatField(null=True, blank=True)
    corners_away_win_odds = models.FloatField(null=True, blank=True)
    
    # Advanced Stats
    statistics_data = models.JSONField(null=True, blank=True)
    predictions_data = models.JSONField(null=True, blank=True)
    h2h_data = models.JSONField(null=True, blank=True)
    
    # Granular Stats Fields (Imported)
    home_shots = models.IntegerField(null=True, blank=True)
    away_shots = models.IntegerField(null=True, blank=True)
    home_shots_on_target = models.IntegerField(null=True, blank=True)
    away_shots_on_target = models.IntegerField(null=True, blank=True)
    home_shots_off_target = models.IntegerField(null=True, blank=True)
    away_shots_off_target = models.IntegerField(null=True, blank=True)
    home_corners = models.IntegerField(null=True, blank=True)
    away_corners = models.IntegerField(null=True, blank=True)
    home_fouls = models.IntegerField(null=True, blank=True)
    away_fouls = models.IntegerField(null=True, blank=True)
    home_yellow = models.IntegerField(null=True, blank=True)
    away_yellow = models.IntegerField(null=True, blank=True)
    home_red = models.IntegerField(null=True, blank=True)
    away_red = models.IntegerField(null=True, blank=True)
    
    # Live Radar Fields
    home_possession = models.IntegerField(null=True, blank=True)
    away_possession = models.IntegerField(null=True, blank=True)
    home_dangerous_attacks = models.IntegerField(null=True, blank=True)
    away_dangerous_attacks = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['date']
        constraints = [
            models.UniqueConstraint(
                fields=['home_team', 'away_team', 'date'], 
                name='unique_match_fixture'
            )
        ]

    @property
    def total_goals(self):
        if self.home_score is not None and self.away_score is not None:
            return self.home_score + self.away_score
        return None

    @property
    def over_25_prob(self):
        h = self.home_team.get_stats("over25")
        a = self.away_team.get_stats("over25")
        return (h + a) // 2

    @property
    def under_15_prob(self):
        h = self.home_team.get_stats("under15")
        a = self.away_team.get_stats("under15")
        return (h + a) // 2

    @property
    def slug(self):
        return slugify(f"{self.home_team.name}-vs-{self.away_team.name}")

    def __str__(self):
        return f"{self.home_team} {self.home_score} x {self.away_score} {self.away_team}"

class Goal(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='goals')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='goals_scored')
    player_name = models.CharField(max_length=100)
    minute = models.IntegerField()
    is_own_goal = models.BooleanField(default=False)
    is_penalty = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.player_name} ({self.minute}')"


class Player(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')
    name = models.CharField(max_length=100)
    age = models.IntegerField(default=0)
    nationality = models.CharField(max_length=50, blank=True, null=True)
    # We can add more fields like position later

    def __str__(self):
        return f"{self.name} ({self.team.name})"


class Season(models.Model):
    year = models.IntegerField(help_text="Ano de término da temporada (Ex: 2024 para 2023/24)")

    def __str__(self):
        return f"{self.year-1}/{self.year}"

class LeagueStanding(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='standings')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='standings')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='standings')
    group_name = models.CharField(max_length=100, default="Regular Season", help_text="Ex: Regular Season, Championship Round")
    
    position = models.IntegerField()
    played = models.IntegerField()
    won = models.IntegerField()
    drawn = models.IntegerField()
    lost = models.IntegerField()
    goals_for = models.IntegerField()
    goals_against = models.IntegerField()
    points = models.IntegerField()

    # Campos específicos para Promedios (Argentina)
    points_prev_prev_season = models.IntegerField(default=0, null=True, blank=True)
    points_prev_season = models.IntegerField(default=0, null=True, blank=True)
    points_curr_season = models.IntegerField(default=0, null=True, blank=True)
    points_per_game = models.FloatField(default=0.0, null=True, blank=True)

    class Meta:
        ordering = ['season', 'league', 'group_name', 'position']
        unique_together = ['league', 'season', 'team', 'group_name']

    def __str__(self):
        return f"{self.season} - {self.team} ({self.position}º)"


class TeamGoalTiming(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='goal_timings')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='goal_timings')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='goal_timings')
    
    # Scored
    scored_0_15 = models.IntegerField(default=0)
    scored_16_30 = models.IntegerField(default=0)
    scored_31_45 = models.IntegerField(default=0)
    scored_46_60 = models.IntegerField(default=0)
    scored_61_75 = models.IntegerField(default=0)
    scored_76_90 = models.IntegerField(default=0)
    
    # Conceded
    conceded_0_15 = models.IntegerField(default=0)
    conceded_16_30 = models.IntegerField(default=0)
    conceded_31_45 = models.IntegerField(default=0)
    conceded_46_60 = models.IntegerField(default=0)
    conceded_61_75 = models.IntegerField(default=0)
    conceded_76_90 = models.IntegerField(default=0)
    
    # Halves
    scored_1st_half = models.IntegerField(default=0)
    scored_2nd_half = models.IntegerField(default=0)
    conceded_1st_half = models.IntegerField(default=0)
    conceded_2nd_half = models.IntegerField(default=0)
    
    # Averages (Calculated minutes)
    avg_min_scored = models.IntegerField(default=0, null=True, blank=True)
    avg_min_conceded = models.IntegerField(default=0, null=True, blank=True)
    
    class Meta:
        ordering = ['league', 'season', 'team']
        unique_together = ['league', 'season', 'team']

    def __str__(self):
        return f"{self.team} - Goal Timing ({self.season})"

class APIUsage(models.Model):
    api_name = models.CharField(max_length=100, help_text="Nome da API/Chave (ex: The Odds API - Live)")
    credits_used = models.IntegerField(default=0, help_text="Créditos usados na última requisição")
    credits_remaining = models.IntegerField(default=0, help_text="Créditos restantes retornados no header")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.api_name}: {self.credits_remaining} restantes (em {self.last_updated.strftime('%d/%m %H:%M')})"

class BetTicket(models.Model):
    TICKET_TYPES = (
        ('Double', 'Dupla'),
        ('Treble', 'Tripla'),
        ('Multiple_4_5', 'Múltipla (4-5 Jogos)'),
        ('Super_6_8', 'Super Múltipla (6-8 Jogos)'),
        ('Hedge_Favorito', 'Hedge ao Favorito'),
        ('Trixie', 'Trixie'),
    )
    STATUS_CHOICES = (
        ('Pending', 'Pendente'),
        ('Green', 'Green ✅'),
        ('Red', 'Red ❌'),
        ('Void', 'Anulada'),
    )

    title = models.CharField(max_length=200, help_text="Título do bilhete (ex: Dupla de Ouro HT)")
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPES)
    strategy = models.CharField(max_length=50, blank=True, null=True, help_text="Nome da estratégia (ex: TRIXIE_DC_GOALS)")
    average_probability = models.IntegerField(default=0, help_text="Probabilidade média de acerto (%)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    date_target = models.DateField(null=True, blank=True, help_text="Data alvo dos jogos deste bilhete")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    @property
    def pending_selections_count(self):
        return self.selections.filter(status='Pending').count()

    @property
    def total_odd(self):
        """
        Retorna a odd total combinada (multiplicada) do bilhete.
        """
        total = 1.0
        selections = self.selections.all()
        if not selections:
            return 0.0
        for sel in selections:
            total *= float(sel.odd)
        return round(total, 2)


class BetTicketSelection(models.Model):
    ticket = models.ForeignKey(BetTicket, on_delete=models.CASCADE, related_name='selections')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='ticket_selections')
    prediction_market = models.CharField(max_length=100, help_text="Mercado escolhido (ex: over_15, ht_goal, home_win)")
    prediction_label = models.CharField(max_length=100, help_text="Rótulo amigável (ex: Mais de 1.5 Gols FT)")
    probability = models.IntegerField(default=0, help_text="Probabilidade específica deste jogo")
    status = models.CharField(max_length=20, choices=BetTicket.STATUS_CHOICES, default='Pending')
    odds_val = models.FloatField(null=True, blank=True, help_text="Odd gravada no momento da geracao")

    def __str__(self):
        return f"{self.match} -> {self.prediction_label} ({self.status})"

    @property
    def odd(self):
        """
        Retorna a odd estimada/real para esta seleção.
        Tenta buscar a odd real do 1X2 se for um mercado de vencedor/dupla chance.
        Caso contrário, calcula a odd estatística implícita baseada na probabilidade.
        """
        if self.status == 'Void':
            return 1.0
        if self.odds_val is not None:
            return round(self.odds_val, 2)
        m = self.match
        market = self.prediction_market.lower()
        
        # 1. Se for mercado 1X2 e tivermos odds reais no banco
        if market == 'home_win' and m.home_team_win_odds:
            return round(m.home_team_win_odds, 2)
        elif market == 'away_win' and m.away_team_win_odds:
            return round(m.away_team_win_odds, 2)
        elif market == 'draw' and m.draw_odds:
            return round(m.draw_odds, 2)
            
        # 2. Se for dupla chance e tivermos as odds de 1X2
        if market == 'double_chance_1x' and m.home_team_win_odds and m.draw_odds:
            inv_odd = (1.0 / m.home_team_win_odds) + (1.0 / m.draw_odds)
            return round(1.0 / inv_odd, 2) if inv_odd > 0 else 1.20
        elif market == 'double_chance_x2' and m.away_team_win_odds and m.draw_odds:
            inv_odd = (1.0 / m.away_team_win_odds) + (1.0 / m.draw_odds)
            return round(1.0 / inv_odd, 2) if inv_odd > 0 else 1.20
        elif market == 'double_chance_12' and m.home_team_win_odds and m.away_team_win_odds:
            inv_odd = (1.0 / m.home_team_win_odds) + (1.0 / m.away_team_win_odds)
            return round(1.0 / inv_odd, 2) if inv_odd > 0 else 1.20
            
        # 3. Fallback: calcula a odd implícita estatística com base na probabilidade com 7% de margem
        prob = self.probability or 50
        implied = 100.0 / prob
        adjusted = implied * 0.93  # 7% bookmaker margin
        return round(max(adjusted, 1.05), 2)


class ScannerTip(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pendente'),
        ('GREEN', 'Green ✅'),
        ('RED', 'Red ❌'),
        ('VOID', 'Anulada ➖'),
    )
    
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='scanner_tips')
    market = models.CharField(max_length=50, help_text="Market identifier (e.g., HT_GOAL, OVER_15, BTTS, HOME_WIN)")
    probability = models.FloatField(default=0.0)
    prediction_text = models.CharField(max_length=200, help_text="User-friendly text (e.g., 'Gol no 1º Tempo')")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['match', 'market']
        
    def __str__(self):
        return f"[{self.status}] {self.match} - {self.prediction_text} ({self.probability}%)"

    @property
    def odd(self):
        """
        Retorna a odd estimada/real para esta dica do scanner.
        """
        m = self.match
        market = self.market.upper()
        
        # 1. Odds reais do 1X2 se disponíveis
        if market == 'HOME_WIN' and m.home_team_win_odds:
            return round(m.home_team_win_odds, 2)
        elif market == 'AWAY_WIN' and m.away_team_win_odds:
            return round(m.away_team_win_odds, 2)
        elif market == 'DRAW' and m.draw_odds:
            return round(m.draw_odds, 2)
            
        # 2. Dupla chance
        elif market == 'DC_1X':
            if m.dc_1x_odds: return round(m.dc_1x_odds, 2)
            if m.home_team_win_odds and m.draw_odds:
                inv_odd = (1.0 / m.home_team_win_odds) + (1.0 / m.draw_odds)
                return round(1.0 / inv_odd, 2) if inv_odd > 0 else 1.20
        elif market == 'DC_X2':
            if m.dc_x2_odds: return round(m.dc_x2_odds, 2)
            if m.away_team_win_odds and m.draw_odds:
                inv_odd = (1.0 / m.away_team_win_odds) + (1.0 / m.draw_odds)
                return round(1.0 / inv_odd, 2) if inv_odd > 0 else 1.20
                
        # 3. Odds Reais de Ambas Marcam
        elif market == 'BTTS' and m.btts_yes_odds:
            return round(m.btts_yes_odds, 2)
            
        # Especiais
        elif market == 'DNB_HOME' and m.dnb_home_odds: return round(m.dnb_home_odds, 2)
        elif market == 'DNB_AWAY' and m.dnb_away_odds: return round(m.dnb_away_odds, 2)
        elif market == 'CLEAN_SHEET_HOME' and m.clean_sheet_home_odds: return round(m.clean_sheet_home_odds, 2)
        elif market == 'CLEAN_SHEET_AWAY' and m.clean_sheet_away_odds: return round(m.clean_sheet_away_odds, 2)
            
        # 4. Odds Reais de Gols (Over)
        elif market == 'HT_GOAL' and m.ht_goal_odds: return round(m.ht_goal_odds, 2)
        elif market == 'OVER_15' and m.over_15_odds: return round(m.over_15_odds, 2)
        elif market == 'OVER_25' and m.over_25_odds: return round(m.over_25_odds, 2)
        elif market == 'OVER_35' and m.over_35_odds: return round(m.over_35_odds, 2)
        elif market == 'OVER_45' and m.over_45_odds: return round(m.over_45_odds, 2)
        elif market == 'OVER_55' and m.over_55_odds: return round(m.over_55_odds, 2)
            
        # 5. Odds Reais de Gols (Under)
        elif market == 'UNDER_25' and m.under_25_odds: return round(m.under_25_odds, 2)
        elif market == 'UNDER_35' and m.under_35_odds: return round(m.under_35_odds, 2)
        elif market == 'UNDER_45' and m.under_45_odds: return round(m.under_45_odds, 2)
        elif market == 'UNDER_55' and m.under_55_odds: return round(m.under_55_odds, 2)
        
        # Dupla Chance & Over
        elif market == 'DC_1X_OVER_1_5' and m.dc_1x_over_15_odds: return round(m.dc_1x_over_15_odds, 2)
        elif market == 'DC_1X_OVER_2_5' and m.dc_1x_over_25_odds: return round(m.dc_1x_over_25_odds, 2)
        elif market == 'DC_1X_OVER_3_5' and m.dc_1x_over_35_odds: return round(m.dc_1x_over_35_odds, 2)
        elif market == 'DC_X2_OVER_1_5' and m.dc_x2_over_15_odds: return round(m.dc_x2_over_15_odds, 2)
        elif market == 'DC_X2_OVER_2_5' and m.dc_x2_over_25_odds: return round(m.dc_x2_over_25_odds, 2)
        elif market == 'DC_X2_OVER_3_5' and m.dc_x2_over_35_odds: return round(m.dc_x2_over_35_odds, 2)
        
        # Dupla Chance & BTTS
        elif market == 'DC_1X_BTTS_YES' and m.dc_1x_btts_yes_odds: return round(m.dc_1x_btts_yes_odds, 2)
        elif market == 'DC_1X_BTTS_NO' and m.dc_1x_btts_no_odds: return round(m.dc_1x_btts_no_odds, 2)
        elif market == 'DC_X2_BTTS_YES' and m.dc_x2_btts_yes_odds: return round(m.dc_x2_btts_yes_odds, 2)
        elif market == 'DC_X2_BTTS_NO' and m.dc_x2_btts_no_odds: return round(m.dc_x2_btts_no_odds, 2)
        
        # Escanteios
        elif market == 'CORNERS_OVER_65' and m.corners_over_65_odds: return round(m.corners_over_65_odds, 2)
        elif market == 'CORNERS_OVER_75' and m.corners_over_75_odds: return round(m.corners_over_75_odds, 2)
        elif market == 'CORNERS_OVER_85' and m.corners_over_85_odds: return round(m.corners_over_85_odds, 2)
        elif market == 'CORNERS_OVER_95' and m.corners_over_95_odds: return round(m.corners_over_95_odds, 2)
        elif market == 'CORNERS_OVER_105' and m.corners_over_105_odds: return round(m.corners_over_105_odds, 2)
        elif market == 'CORNERS_OVER_115' and m.corners_over_115_odds: return round(m.corners_over_115_odds, 2)
        elif market == 'CORNERS_HOME' and m.corners_home_win_odds: return round(m.corners_home_win_odds, 2)
        elif market == 'CORNERS_DRAW' and m.corners_draw_odds: return round(m.corners_draw_odds, 2)
        elif market == 'CORNERS_AWAY' and m.corners_away_win_odds: return round(m.corners_away_win_odds, 2)
            
        # 6. Fallback implícito estatístico (Simulação Realista)
        # O robô gera a probabilidade pelo histórico de acertos (ex: 85%).
        # As casas de apostas puxam essa probabilidade para baixo para embutir a margem de lucro.
        # Aplicamos um 'deflator' de 0.82 que aproxima perfeitamente o número gerado à Odd da Bet365.
        prob = self.probability or 50
        bookmaker_implied_prob = prob * 0.82
        
        # Se a probabilidade for muito alta, garantimos que a odd não fique bizarra (menor que 1.10)
        adjusted = 100.0 / bookmaker_implied_prob
        return round(max(adjusted, 1.10), 2)

class LiveMatchSnapshot(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='snapshots')
    timestamp = models.DateTimeField(auto_now_add=True)
    minute = models.IntegerField(default=0)
    
    home_shots_on_target = models.IntegerField(default=0)
    away_shots_on_target = models.IntegerField(default=0)
    home_shots_off_target = models.IntegerField(default=0)
    away_shots_off_target = models.IntegerField(default=0)
    
    home_corners = models.IntegerField(default=0)
    away_corners = models.IntegerField(default=0)
    
    home_dangerous_attacks = models.IntegerField(default=0)
    away_dangerous_attacks = models.IntegerField(default=0)
    
    home_possession = models.IntegerField(default=50)
    away_possession = models.IntegerField(default=50)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Snapshot {self.match} at {self.minute}'"
