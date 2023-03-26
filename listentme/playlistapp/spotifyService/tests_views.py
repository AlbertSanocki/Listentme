import os
import json
from requests import Response
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status

class BaseViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        os.environ['REDIRECT_URI'] = 'http://example.com/callback'
        os.environ['CLIENT_SECRET'] = 'example_client_secret'
        os.environ['CLIENT_ID'] = 'example_client_id'
        self.expected_scopes = 'user-read-playback-state user-modify-playback-state user-read-currently-playing \
            playlist-read-private playlist-modify-private playlist-modify-public \
            ugc-image-upload playlist-read-collaborative'

class AuthURLViewTestCase(BaseViewTestCase):

    @patch('playlistapp.spotifyService.views.Request')
    def test_auth_url(self, mock_request):

        expected_params = {
            'scope': self.expected_scopes,
            'response_type': 'code',
            'redirect_uri': 'http://example.com/callback',
            'client_id': 'example_client_id',
        }

        mock_request.return_value.prepare.return_value.url = 'http://example.com'
        response = self.client.get(reverse('playlistapp:get_auth_url'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, 'http://example.com')
        mock_request.assert_called_once_with('GET', 'https://accounts.spotify.com/authorize', params=expected_params)

class SpotifyCallbackTestCase(BaseViewTestCase):

    @patch('playlistapp.spotifyService.views.post')
    @patch('playlistapp.spotifyService.views.update_or_create_user_tokens')
    def test_spotify_callback(self, mock_update_or_create_user_tokens, mock_post):
        expected_code = 'expected_code'
        test_access_token = 'test_access_token'
        test_token_type = 'Bearer'
        test_expires_in = 3600
        test_refresh_token = 'test_refresh_token'
        response_dict = {
            'access_token': test_access_token,
            'token_type': test_token_type,
            'expires_in': test_expires_in,
            'refresh_token': test_refresh_token,
        }
        response_str = json.dumps(response_dict)
        mock_http_response = Response()
        mock_http_response._content = response_str.encode('utf-8')
        mock_http_response.status_code = 200
        mock_post.return_value = mock_http_response

        test_session_key=self.client.session._session_key

        response = self.client.get(reverse('playlistapp:spotify_callback'), {
            'code': expected_code,
            'error': ''
        })
        expected_data = {
        'grant_type': 'authorization_code',
        'code': expected_code,
        'redirect_uri': 'http://example.com/callback',
        'client_id': 'example_client_id',
        'client_secret': 'example_client_secret',
        }
        self.assertRedirects(response, reverse('playlistapp:home'))
        mock_post.assert_called_once_with('https://accounts.spotify.com/api/token', data=expected_data)
        mock_update_or_create_user_tokens.assert_called_once_with(test_session_key, test_access_token, test_token_type, test_expires_in, test_refresh_token)

    @patch('playlistapp.spotifyService.views.post')
    @patch('django.contrib.sessions.backends.db.SessionStore.create')
    @patch('playlistapp.spotifyService.views.update_or_create_user_tokens')
    def test_spotify_callback_no_session_key(self, mock_update_or_create_user_tokens, mock_create, mock_post):
        expected_code = 'expected_code'
        response = self.client.get(reverse('playlistapp:spotify_callback'), {
            'code': expected_code,
            'error': ''
        })
        mock_update_or_create_user_tokens.assert_called_once()
        mock_post.assert_called_once()
        self.assertRedirects(response, reverse('playlistapp:home'))
        mock_create.assert_called_once()

class SpotifyLogoutTestCase(BaseViewTestCase):

    @patch('playlistapp.spotifyService.views.delete_spotify_token')
    def test_spotify_log_out(self, mock_del_token):
        test_session_key=self.client.session._session_key
        response = self.client.get(reverse('playlistapp:spotify_logout'))
        mock_del_token.assert_called_once_with(test_session_key)
        self.assertRedirects(response, reverse('playlistapp:home'))