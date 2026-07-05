from django.urls import path
from . import views

app_name = 'widget_api'

urlpatterns = [
    path('standings/brasileirao/', views.widget_brasileirao_view, name='brasileirao_standings'),
]
