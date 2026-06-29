from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extensão do User padrão do Django para controle de assinatura premium."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_premium = models.BooleanField(default=False, help_text="Usuário tem acesso premium ativo?")
    premium_until = models.DateTimeField(null=True, blank=True, help_text="Data de expiração do premium")
    PLAN_CHOICES = [
        ('popular', 'Popular'),
        ('vip', 'VIP'),
    ]
    plan_type = models.CharField(
        max_length=10,
        choices=PLAN_CHOICES,
        default='popular',
        help_text="Tipo de plano premium do usuário"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "⭐ Premium" if self.is_premium else "Free"
        return f"{self.user.username} ({status})"

    @property
    def is_premium_active(self):
        """Verifica se o premium está ativo (is_premium=True e não expirou)."""
        if not self.is_premium:
            return False
        if self.premium_until is None:
            return True  # Premium sem data de expiração = vitalício
        from django.utils import timezone
        return self.premium_until > timezone.now()

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Cria automaticamente um UserProfile quando um User é criado."""
    if kwargs.get('raw', False):
        return
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Salva o perfil quando o User é salvo."""
    if kwargs.get('raw', False):
        return
    if hasattr(instance, 'profile'):
        instance.profile.save()
