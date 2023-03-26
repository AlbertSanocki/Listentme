"""Spotify Service Views based on Spotify Authorization Code Flow"""
import os
from django.shortcuts import redirect
from rest_framework.views import APIView
from requests import Request, post
from .util import (
    update_or_create_user_tokens,
    delete_spotify_token
)

class AuthURL(APIView):
    """Preparing and redirect to Spotify Authentication url"""
    def get(self, request, format=None):
        """Prepare and redirect to urlresponsible for logging in to Spotify"""
        scopes = 'user-read-playback-state user-modify-playback-state user-read-currently-playing \
            playlist-read-private playlist-modify-private playlist-modify-public \
            ugc-image-upload playlist-read-collaborative'

        url = Request('GET', 'https://accounts.spotify.com/authorize', params={
            'scope': scopes,
            'response_type': 'code',
            'redirect_uri': os.environ.get('REDIRECT_URI'),
            'client_id': os.environ.get('CLIENT_ID'),
        }).prepare().url

        return redirect(url)

def spotify_callback(request, format=None):
    """Returning access and refresh tokens"""
    code = request.GET.get('code')
    error = request.GET.get('error')

    response = post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': os.environ.get('REDIRECT_URI'),
        'client_id': os.environ.get('CLIENT_ID'),
        'client_secret': os.environ.get('CLIENT_SECRET'),
    }).json()

    access_token = response.get('access_token')
    token_type = response.get('token_type')
    refresh_token = response.get('refresh_token')
    expires_in = response.get('expires_in')
    error = response.get('error')

    if not request.session.exists(request.session.session_key):
        request.session.create()

    update_or_create_user_tokens(
        request.session.session_key,
        access_token, token_type,
        expires_in, refresh_token
    )
    return redirect('playlistapp:home')

def spotify_log_out(request, format=None):
    """Logout for the user"""
    delete_spotify_token(request.session.session_key)
    return redirect('playlistapp:home')
