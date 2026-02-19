from django.db import models
from django.utils.text import slugify

class League(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.country})"

class Team(models.Model):
    name = models.CharField(max_length=100)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='teams')
    api_id = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="ID do Time na API")

    def get_stats(self, market="over25"):
        matches = Match.objects.filter(
            models.Q(home_team=self) | models.Q(away_team=self),
            home_score__isnull=False,
            away_score__isnull=False
        ).order_by('-date')[:10]
        
        if not matches:
            return 0
            
        count = 0
        for m in matches:
            total = (m.home_score or 0) + (m.away_score or 0)
            if market == "over25" and total > 2.5:
                count += 1
            elif market == "under15" and total < 1.5:
                count += 1
                
        return int((count / len(matches)) * 100)

    def __str__(self):
        return self.name

class Match(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='matches')
    season = models.ForeignKey('Season', on_delete=models.CASCADE, related_name='matches', null=True)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    date = models.DateTimeField(null=True, blank=True)
    round_name = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, default="Scheduled")
    api_id = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text="ID da Fixture na API")
    elapsed_time = models.IntegerField(null=True, blank=True)

    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    ht_home_score = models.IntegerField(null=True, blank=True)
    ht_away_score = models.IntegerField(null=True, blank=True)
    
    # Advanced Stats
    statistics_data = models.JSONField(null=True, blank=True)
    predictions_data = models.JSONField(null=True, blank=True)
    h2h_data = models.JSONField(null=True, blank=True)
    
    # Granular Stats Fields (Imported)
    home_shots = models.IntegerField(null=True, blank=True)
    away_shots = models.IntegerField(null=True, blank=True)
    home_shots_on_target = models.IntegerField(null=True, blank=True)
    away_shots_on_target = models.IntegerField(null=True, blank=True)
    home_corners = models.IntegerField(null=True, blank=True)
    away_corners = models.IntegerField(null=True, blank=True)
    home_fouls = models.IntegerField(null=True, blank=True)
    away_fouls = models.IntegerField(null=True, blank=True)
    home_yellow = models.IntegerField(null=True, blank=True)
    away_yellow = models.IntegerField(null=True, blank=True)
    home_red = models.IntegerField(null=True, blank=True)
    away_red = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['date']

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
    
    position = models.IntegerField()
    played = models.IntegerField()
    won = models.IntegerField()
    drawn = models.IntegerField()
    lost = models.IntegerField()
    goals_for = models.IntegerField()
    goals_against = models.IntegerField()
    points = models.IntegerField()

    class Meta:
        ordering = ['season', 'league', 'position']
        unique_together = ['league', 'season', 'team']

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
