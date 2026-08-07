from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect, HttpResponse
from django.core.management import call_command
from django.contrib import messages
from .models import League, Team, Match, Season, LeagueStanding, Goal, APIUsage

@admin.register(APIUsage)
class APIUsageAdmin(admin.ModelAdmin):
    list_display = ('api_name', 'credits_remaining', 'last_updated')
    readonly_fields = ('api_name', 'credits_used', 'credits_remaining', 'last_updated')
    
    def has_add_permission(self, request):
        return False

@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'division')
    change_list_template = "admin/matches/league/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('backup-db/', self.admin_site.admin_view(self.backup_db), name='backup-db'),
            path('clean-duplicates/', self.admin_site.admin_view(self.clean_duplicates), name='clean-duplicates'),
        ]
        return my_urls + urls

    def backup_db(self, request):
        try:
            call_command('backup_db')
            self.message_user(request, "Backup gerado com sucesso na pasta do projeto!", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Erro ao gerar backup: {e}", messages.ERROR)
        return HttpResponseRedirect("../")

    def clean_duplicates(self, request):
        try:
            call_command('merge_all_historical_duplicates')
            call_command('recalculate_standings', all=True, smart=True)
            self.message_user(request, "Limpeza de duplicatas e recálculo concluídos!", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Erro na limpeza: {e}", messages.ERROR)
        return HttpResponseRedirect("../")

admin.site.register(Team)
admin.site.register(Match)
admin.site.register(Goal)
admin.site.register(Season)
admin.site.register(LeagueStanding)
