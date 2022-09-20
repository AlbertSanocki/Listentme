"""Utils for Spotify Service"""
import json
import os
from datetime import timedelta
from django.utils import timezone
from requests import post, put, get
from .models import SpotifyToken


BASE_URL = os.environ.get('BASE_URL')

def get_user_tokens(session_id):
    """Load and return user token stored in database"""
    user_tokens = SpotifyToken.objects.filter(user=session_id)
    if user_tokens.exists():
        return user_tokens[0]
    return None

def update_or_create_user_tokens(session_id, access_token, token_type, expires_in, refresh_token):
    """Update user token if exists or create new one and save it
    variables required by Spotify API: access_token, token_type, expires_in, refresh_token
    """
    tokens = get_user_tokens(session_id)
    expires_in = timezone.now() + timedelta(seconds=expires_in)

    if tokens:
        tokens.access_token = access_token
        tokens.refresh_token = refresh_token
        tokens.expires_in = expires_in
        tokens.token_type = token_type
        tokens.save(update_fields=['access_token', 'refresh_token', 'expires_in', 'token_type'])
    else:
        tokens = SpotifyToken(
            user=session_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            expires_in=expires_in
        )
        tokens.save()

def is_spotify_authenticated(session_id):
    """Check if user is authenticated with Spotify"""
    tokens = get_user_tokens(session_id)
    if not tokens:
        return False
    if tokens.expires_in <= timezone.now():
        refresh_spotify_token(session_id)
    return True


def refresh_spotify_token(session_id):
    """Refresh user token using Spotify API"""
    refresh_token = get_user_tokens(session_id).refresh_token

    response = post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': os.environ.get('CLIENT_ID'),
        'client_secret': os.environ.get('CLIENT_SECRET'),
    }).json()

    access_token = response.get('access_token')
    token_type = response.get('token_type')
    expires_in = response.get('expires_in')

    update_or_create_user_tokens(session_id, access_token, token_type, expires_in, refresh_token)

def delete_spotify_token(session_id):
    """Delete auth token of currentl user"""
    user_tokens = SpotifyToken.objects.filter(user=session_id)
    if user_tokens.exists():
        user_tokens.delete()
    return None

def execute_spotify_api_request(
        session_id,
        endpoint,
        post_=False,
        put_=False,
        get_=False,
        data=None,
        params=None
    ):
    """Process every Spotify API request"""
    tokens = get_user_tokens(session_id)
    headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + tokens.access_token}

    if post_:
        response = post(BASE_URL + endpoint, params=params, data=data, headers=headers)
    if put_:
        response = put(BASE_URL + endpoint, params=params, data=data, headers=headers)
    if get_:
        response = get(BASE_URL + endpoint, params=params, data=data, headers=headers)

    try:
        return response.json()
    except:
        return {'Error': 'Issue with request'}

def get_current_user(session_id):
    """Get data of user authenticated with Spotify"""
    endpoint='me/'
    if not is_spotify_authenticated(session_id):
        return None
    if is_spotify_authenticated(session_id):
        execute_spotify_api_request(session_id, endpoint, get_=True)
        response = execute_spotify_api_request(session_id, endpoint, get_=True)
        try:
            current_user = {
                'display_name': response.get('display_name'),
                'external_url': response.get('external_urls').get('spotify'),
                'image_url': response.get('images')[0].get('url'),
                'id': response.get('id'),
            }
        except IndexError:
            current_user = {
                'display_name': response.get('display_name'),
                'external_url': response.get('external_urls').get('spotify'),
                'id': response.get('id'),
            }
        return current_user


def create_a_playlist(session_id, form_data):
    """Creating a playlist in authenticated Spotify user account
    according to preferences
    """
    current_user = get_current_user(session_id)
    user_id = current_user.get('id')
    endpoint = f'users/{user_id}/playlists'
    new_playlist_data = json.dumps({
        'name' : form_data.get('name'),
        'description' : form_data.get('description'),
        'public' : form_data.get('public')
    })
    new_playlist = execute_spotify_api_request(
        session_id,
        endpoint,
        post_=True,
        data=new_playlist_data
    )
    new_palylist_id = new_playlist.get('id')
    artists_form = form_data.get('artists')
    artists_data = get_artists(session_id, artists_form)
    tracks_uris_str = get_artists_top_tracks_uris(session_id, artists_data)
    add_tracks_to_playlist(session_id, new_palylist_id, tracks_uris_str)

def get_artists(session_id, artists_form):
    """Search and return an Artist from Spotify"""
    endpoint = 'search/'
    artists_data = []
    for artist in artists_form:
        params = {
            'q': artist,
            'type': 'artist',
            'limit': 1,
        }
        response = execute_spotify_api_request(
            session_id,
            endpoint,
            get_=True,
            params=params
        ).get('artists').get('items')[0]
        try:
            artists_data.append({
                'name': response.get('name'),
                'id': response.get('id'),
                'external_url': response.get('external_urls').get('spotify'),
                'image_url': response.get('images')[0].get('url'),
            })
        except IndexError:
            artists_data.append({
                'name': response.get('name'),
                'id': response.get('id'),
                'external_url': response.get('external_urls').get('spotify'),
            })
    return artists_data

def get_artists_top_tracks_uris(session_id, artists_data):
    """Return top tracks of artists chosen in form"""
    tracks_uris_list = []
    for artist in artists_data:
        artist_id = artist.get('id')
        endpoint = f'artists/{artist_id}/top-tracks?market=US'
        response = execute_spotify_api_request(session_id, endpoint, get_=True).get('tracks')
        for track in response:
            tracks_uris_list.append(track.get('uri'))
    tracks_uris_str = ','.join(tracks_uris_list)
    return tracks_uris_str

def add_tracks_to_playlist(session_id, playlist_id, tracks_uris_str):
    """Add tracks to playlist using tracks uris"""
    endpoint = f'playlists/{playlist_id}/tracks'

    params = {
        'uris': tracks_uris_str
    }
    execute_spotify_api_request(session_id, endpoint, post_=True, params=params)

def get_current_users_playlists(session_id):
    """Load all playlists of the currently logged user"""
    endpoint = 'me/playlists'
    params = {
        'limit': 20
    }
    users_playlists = []
    if is_spotify_authenticated(session_id):
        response = execute_spotify_api_request(
            session_id,
            endpoint,
            get_=True,
            params=params
        ).get('items')
        for playlist in response:
            try:
                users_playlists.append({
                    'name': playlist.get('name'),
                    'external_url': playlist.get('external_urls').get('spotify'),
                    'image_url': playlist.get('images')[0].get('url'),
                    'id': playlist.get('id'),
                })
            except IndexError:
                users_playlists.append({
                    'name': playlist.get('name'),
                    'external_url': playlist.get('external_urls').get('spotify'),
                    'id': playlist.get('id'),
                })
        return users_playlists
    return None
