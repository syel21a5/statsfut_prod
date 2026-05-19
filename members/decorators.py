from functools import wraps
from django.shortcuts import redirect


def premium_required(view_func):
    """
    Decorator que exige que o usuário esteja logado E tenha premium ativo.
    Redireciona para login se não logado, ou para paywall se não premium.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('members:login')
        if not hasattr(request.user, 'profile') or not request.user.profile.is_premium_active:
            return redirect('members:paywall')
        return view_func(request, *args, **kwargs)
    return _wrapped
