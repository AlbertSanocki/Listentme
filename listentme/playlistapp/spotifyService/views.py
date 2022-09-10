"""Spotify Service Views based on Spotify Authorization Code Flow"""
import os
from django.shortcuts import redirect
from rest_framework.views import APIView
from requests import Request, post
from rest_framework import status
from rest_framework.response import Response
from .util import (
    is_spotify_authenticated,
    update_or_create_user_tokens,
    execute_spotify_api_request,
    delete_spotify_token
)

class AuthURL(APIView):
    """Preparing and redirect to Spotify Authentication url"""
    def get(self, request, format=None):
        """Prepare and redirect to urlresponsible for logging in to Spotify"""
        scopes = 'user-read-playback-state user-modify-playback-state user-read-currently-playing \
            playlist-read-private playlist-modify-private playlist-modify-public playlist-read-collaborative'

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

class IsAuthenticated(APIView):
    """IsAuthenticated Rest API View for a future frontend"""
    def get(self, request, format=None):
        """
        Check if Spotify user is authenticated
        """
        is_authenticated = is_spotify_authenticated(self.request.session.session_key)
        return Response({'status': is_authenticated}, status=status.HTTP_200_OK)

class CurrentUser(APIView):
    """CurrentUser Rest API View for a future frontend"""
    def get(self, request):
        """
        Load current user
        """
        endpoint = 'me/'
        print(self.request.session.session_key)
        is_authenticated = is_spotify_authenticated(self.request.session.session_key)
        print(is_authenticated)
        if is_authenticated:
            current_user = execute_spotify_api_request(request.session.session_key, endpoint)
            return Response({'current_user': current_user}, status=status.HTTP_200_OK)
        return Response({'current_user': None}, status=status.HTTP_200_OK)
