from django.contrib import admin
from .models import League, Team, Match, Season, LeagueStanding, Goal, APIUsage

@admin.register(APIUsage)
class APIUsageAdmin(admin.ModelAdmin):
    list_display = ('api_name', 'credits_remaining', 'last_updated')
    readonly_fields = ('api_name', 'credits_used', 'credits_remaining', 'last_updated')
    
    def has_add_permission(self, request):
        return False

admin.site.register(League)
admin.site.register(Team)
admin.site.register(Match)
admin.site.register(Goal)
admin.site.register(Season)
admin.site.register(LeagueStanding)
