from django.contrib import admin
from .models import League, Team, Match, Season, LeagueStanding, Goal

admin.site.register(League)
admin.site.register(Team)
admin.site.register(Match)
admin.site.register(Goal)
admin.site.register(Season)
admin.site.register(LeagueStanding)
