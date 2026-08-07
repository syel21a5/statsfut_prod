from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class CustomLoginForm(AuthenticationForm):
    """Formulário de login com estilo dark theme."""
    username = forms.CharField(
        label=_("Username"),
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': _('Your username'),
            'autofocus': True,
            'id': 'id_login_username',
        })
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': _('Your password'),
            'id': 'id_login_password',
        })
    )


class CustomRegisterForm(UserCreationForm):
    """Formulário de registro com estilo dark theme."""
    email = forms.EmailField(
        label=_("Email"),
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control bg-dark text-white border-secondary',
            'placeholder': _('your@email.com'),
            'id': 'id_register_email',
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dark_attrs = {
            'class': 'form-control bg-dark text-white border-secondary',
        }
        self.fields['username'].widget.attrs.update({
            **dark_attrs,
            'placeholder': _('Choose a username'),
            'id': 'id_register_username',
        })
        self.fields['password1'].widget.attrs.update({
            **dark_attrs,
            'placeholder': _('Create a password'),
            'id': 'id_register_password1',
        })
        self.fields['password2'].widget.attrs.update({
            **dark_attrs,
            'placeholder': _('Confirm your password'),
            'id': 'id_register_password2',
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
