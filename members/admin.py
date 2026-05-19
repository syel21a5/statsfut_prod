from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


# Inline de Perfil para editar o Premium dentro do cadastro do próprio Usuário
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Premium & Assinatura'
    fk_name = 'user'


# Customização da tela de gestão de Usuários
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    
    # Adiciona coluna indicando se é premium na listagem de usuários
    def get_is_premium(self, instance):
        try:
            return instance.profile.is_premium
        except UserProfile.DoesNotExist:
            return False
    get_is_premium.boolean = True
    get_is_premium.short_description = 'Premium?'

    list_display = BaseUserAdmin.list_display + ('get_is_premium',)


# Desregistra o Admin padrão e registra o nosso customizado
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# Mantém o registro individual do perfil para edições rápidas em lote
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_premium', 'premium_until', 'created_at')
    list_filter = ('is_premium',)
    search_fields = ('user__username', 'user__email')
    list_editable = ('is_premium', 'premium_until')
    readonly_fields = ('created_at',)
