from django.urls import path
from . import views

urlpatterns = [
    path('', views.VideoMakerView.as_view(), name='video_maker'),
]
