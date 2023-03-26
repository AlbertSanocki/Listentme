"""playlistapp URLS"""
from django.urls import path
from .views import home, create, view
from .spotifyService.views import AuthURL, spotify_callback, spotify_log_out

app_name = 'playlistapp'

urlpatterns = [
    path('', home, name='home'),
    path('create', create, name='create'),
    path('view', view, name='view'),
    path('spotify/get-auth-url', AuthURL.as_view(), name='get_auth_url'),
    path('spotify/redirect', spotify_callback, name='spotify_callback'),
    path('logout', spotify_log_out, name='spotify_logout'),
]
