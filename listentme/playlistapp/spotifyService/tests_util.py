"""Tests for util.py"""
import os
import json
import base64
from datetime import datetime, timedelta
from requests import Response
from unittest.mock import patch, MagicMock, call
from PIL import Image
import tempfile
from django.utils import timezone
from django.test import TestCase, TransactionTestCase
from .models import SpotifyToken
from .util import (
    get_user_tokens,
    update_or_create_user_tokens,
    is_spotify_authenticated,
    refresh_spotify_token,
    delete_spotify_token,
    execute_spotify_api_request,
    get_current_user,
    add_custom_image_to_playlist,
    get_artists,
    get_artists_top_tracks_uris,
    add_tracks_to_playlist,
    create_a_playlist,
    get_current_users_playlists,
)

class BaseTestCase(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user_id = 'Valid_ID'
        self.token = SpotifyToken.objects.create(
            user = self.user_id,
            created_at = datetime(2023, 3, 11, 15, 0, 0, microsecond=0, tzinfo=timezone.utc),
            refresh_token = 'TestRefreshToken',
            access_token = 'TestAccessToken',
            expires_in = datetime(2023, 3, 11, 16, 0, 0, microsecond=0, tzinfo=timezone.utc),
            token_type = 'Bearer'
        )

    def tearDown(self) -> None:
        SpotifyToken.objects.all().delete()

class GetUserTokenTestCase(BaseTestCase):

    def test_get_user_tokens_existing(self):
        valid_user_id = self.user_id
        token = get_user_tokens(session_id=valid_user_id)
        self.assertEqual(token, self.token)

    def test_get_user_tokens_non_existing(self):
        invalid_user_id = 'Non_Existing_ID'
        token = get_user_tokens(session_id=invalid_user_id)
        self.assertEqual(token, None)

class UpdateOrCreateUserTokenTestCase(BaseTestCase):

    def test_update_user_tokens(self):
        session_id = self.user_id
        access_token = 'UpdatedAccessToken'
        token_type = 'Bearer'
        expires_in = 3600
        refresh_token = 'UpdatedRefreshToken'
        update_or_create_user_tokens(session_id,access_token,token_type,expires_in,refresh_token)
        updated_tokens = SpotifyToken.objects.get(user=self.user_id)
        expected_expires_in = timezone.now() + timedelta(seconds=expires_in)
        self.assertIsInstance(updated_tokens, SpotifyToken)
        self.assertEqual(updated_tokens.user, self.user_id)
        self.assertEqual(updated_tokens.access_token, 'UpdatedAccessToken')
        self.assertEqual(updated_tokens.refresh_token, 'UpdatedRefreshToken')
        self.assertEqual(updated_tokens.token_type, 'Bearer')
        self.assertAlmostEqual(
            updated_tokens.expires_in.timestamp(),
            expected_expires_in.timestamp(),
            delta=1
        )

    def test_create_user_tokens(self):
        invalid_user_id = 'Non_Existing_ID'
        session_id = invalid_user_id
        access_token = 'NewAccessToken'
        token_type = 'Bearer'
        expires_in = 3600
        refresh_token = 'NewRefreshToken'
        update_or_create_user_tokens(session_id, access_token,token_type,expires_in,refresh_token)
        new_tokens = SpotifyToken.objects.get(user=invalid_user_id)
        expected_expires_in = timezone.now() + timedelta(seconds=expires_in)
        self.assertIsInstance(new_tokens, SpotifyToken)
        self.assertEqual(new_tokens.user, invalid_user_id)
        self.assertEqual(new_tokens.access_token, 'NewAccessToken')
        self.assertEqual(new_tokens.refresh_token, 'NewRefreshToken')
        self.assertEqual(new_tokens.token_type, 'Bearer')
        self.assertAlmostEqual(
            new_tokens.expires_in.timestamp(),
            expected_expires_in.timestamp(),
            delta=1
        )

class RefreshSpotifyTokenTestCase(BaseTestCase):

    @patch('playlistapp.spotifyService.util.post')
    def test_refresh_spotify_token(self, mock_post):

        os.environ['CLIENT_ID'] = 'test_client_id'
        os.environ['CLIENT_SECRET'] = 'test_client_secret'

        session_id = self.token.user
        refresh_token = self.token.refresh_token

        access_token_response = 'TestRefreshAcessToken'
        token_type_response = 'TestRefreshBearer'
        expires_in_response = 3600

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': access_token_response,
            'token_type': token_type_response,
            'expires_in': expires_in_response
        }
        mock_post.return_value = mock_response

        refresh_spotify_token(session_id)

        mock_post.assert_called_once_with(
            'https://accounts.spotify.com/api/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': 'test_client_id',
                'client_secret': 'test_client_secret'
            }
        )
        refreshed_token = SpotifyToken.objects.get(user=session_id)
        self.assertEqual(refreshed_token.access_token, access_token_response)
        self.assertEqual(refreshed_token.token_type, token_type_response)
        self.assertEqual(refreshed_token.refresh_token, refresh_token)

class IsSpotifyAuthenticatedTestCase(BaseTestCase):

    def test_is_spotify_authenticated_true(self):
        session_id = self.user_id
        expiring_seconds = 3600
        self.token.expires_in = timezone.now() + timedelta(seconds=expiring_seconds)
        self.token.save()
        self.assertTrue(is_spotify_authenticated(session_id))

    @patch('playlistapp.spotifyService.util.refresh_spotify_token')
    def test_is_spotify_authenticated_token_expired(self, mock_refresh_spotify_token):
        session_id = 'Valid_ID'
        expiring_seconds = 3600
        self.token.expires_in = timezone.now() - timedelta(seconds=expiring_seconds)
        self.token.save()
        spotify_authenticated = is_spotify_authenticated(session_id)
        mock_refresh_spotify_token.assert_called_once_with(session_id)
        self.assertTrue(spotify_authenticated)

    def test_is_spotify_authenticated_false(self):
        invalid_session_id = 'Non_Existing_ID'
        self.assertFalse(is_spotify_authenticated(invalid_session_id))

class DeteleSpotifyTokenTestCase(BaseTestCase):

    def test_delete_spotify_token(self):
        session_id = self.user_id
        self.assertTrue(SpotifyToken.objects.filter(user=self.user_id).exists())
        delete_spotify_token(session_id)
        self.assertFalse(SpotifyToken.objects.filter(user=self.user_id).exists())

class ExecuteSpotifyApiRequestTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.data = json.dumps({
            'name': 'test_name',
            'description': 'test_description'
        })
        self.params = {
            'param': 'test_param',
            'type': 'test_type'
        }
        self.mock_response = MagicMock()
        self.mock_response.json.return_value = {
            'name': 'test_name_response',
            'description': 'test_description_response'
        }


    @patch('playlistapp.spotifyService.util.post')
    def test_execute_spotify_api_request_post(self, mock_execute_spotify_api_request_post):
        session_id = self.user_id
        endpoint = 'test/post/endpoint'
        request_method = 'POST'

        mock_execute_spotify_api_request_post.return_value = self.mock_response
        response = execute_spotify_api_request(session_id, endpoint, request_method, self.data, self.params)
        mock_execute_spotify_api_request_post.assert_called_once_with(
            'https://api.spotify.com/v1/test/post/endpoint',
            data=self.data,
            params=self.params,
            headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + self.token.access_token}
        )
        self.assertIsInstance(response, dict)
        self.assertEqual(response['name'], 'test_name_response')
        self.assertEqual(response['description'], 'test_description_response')

    @patch('playlistapp.spotifyService.util.put')
    def test_execute_spotify_api_request_put(self, mock_execute_spotify_api_request_put):
        session_id = self.user_id
        endpoint = 'test/put/endpoint'
        request_method = 'PUT'
        mock_execute_spotify_api_request_put.return_value = self.mock_response
        response = execute_spotify_api_request(session_id, endpoint, request_method, self.data, self.params)
        mock_execute_spotify_api_request_put.assert_called_once_with(
            'https://api.spotify.com/v1/test/put/endpoint',
            data=self.data,
            params=self.params,
            headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + self.token.access_token}
        )
        self.assertIsInstance(response, dict)
        self.assertEqual(response['name'], 'test_name_response')
        self.assertEqual(response['description'], 'test_description_response')

    @patch('playlistapp.spotifyService.util.get')
    def test_execute_spotify_api_request_get(self, mock_execute_spotify_api_request_get):
        session_id = self.user_id
        endpoint = 'test/get/endpoint'
        request_method = 'GET'
        mock_execute_spotify_api_request_get.return_value = self.mock_response
        response = execute_spotify_api_request(session_id, endpoint, request_method, self.data, self.params)
        mock_execute_spotify_api_request_get.assert_called_once_with(
            'https://api.spotify.com/v1/test/get/endpoint',
            data=self.data,
            params=self.params,
            headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + self.token.access_token}
        )
        self.assertIsInstance(response, dict)
        self.assertEqual(response['name'], 'test_name_response')
        self.assertEqual(response['description'], 'test_description_response')

    @patch('playlistapp.spotifyService.util.get')
    def test_execute_spotify_api_request_issue_with_request(self, mock_execute_spotify_api_request_get):
        session_id = self.user_id
        endpoint = 'test/get/endpoint'
        request_method = 'GET'
        mock_execute_spotify_api_request_get.return_value = None
        response = execute_spotify_api_request(session_id, endpoint, request_method, self.data, self.params)
        mock_execute_spotify_api_request_get.assert_called_once_with(
            'https://api.spotify.com/v1/test/get/endpoint',
            data=self.data,
            params=self.params,
            headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + self.token.access_token}
        )
        self.assertIsInstance(response, dict)
        self.assertEqual(response['Error'], 'Issue with request')

class GetCurrentUserTestCase(BaseTestCase):
    
    @patch('playlistapp.spotifyService.util.is_spotify_authenticated')
    def test_get_current_user_not_authenticated(self, mock_is_spotify_authenticated):
        session_id = 'Invalid_ID'
        mock_is_spotify_authenticated.return_value = False
        self.assertIsNone(get_current_user(session_id))

    @patch('playlistapp.spotifyService.util.is_spotify_authenticated')
    @patch('playlistapp.spotifyService.util.execute_spotify_api_request')
    def test_get_current_user_valid_user(self, mock_execute_spotify_api_request, mock_is_spotify_authenticated):
        session_id = self.user_id
        endpoint = 'me/'
        mock_is_spotify_authenticated.return_value = True
        mock_response = {
            'display_name': 'test_display_name_response',
            'external_urls': {'spotify': 'test_external_url_response'},
            'images': [{'height': None, 'url': 'test_image_url_response', 'width': None}],
            'id': 'id_response'
        }
        mock_execute_spotify_api_request.return_value = mock_response
        current_user = get_current_user(session_id)
        mock_execute_spotify_api_request.assert_called_once_with(
            session_id,
            endpoint,
            request_method='GET'
        )
        self.assertIsInstance(current_user, dict)
        self.assertEqual(current_user['display_name'],'test_display_name_response')
        self.assertEqual(current_user['external_url'],'test_external_url_response')
        self.assertEqual(current_user['image_url'],'test_image_url_response')
        self.assertEqual(current_user['id'],'id_response')


    @patch('playlistapp.spotifyService.util.is_spotify_authenticated')
    @patch('playlistapp.spotifyService.util.execute_spotify_api_request')
    def test_get_current_user_valid_user_no_image_url(self, mock_execute_spotify_api_request, mock_is_spotify_authenticated):
        session_id = self.user_id
        endpoint = 'me/'
        mock_is_spotify_authenticated.return_value = True
        mock_response = {
            'display_name': 'test_display_name_response',
            'external_urls': {'spotify': 'test_external_url_response'},
            'images': [],
            'id': 'id_response'
        }
        mock_execute_spotify_api_request.return_value = mock_response
        current_user = get_current_user(session_id)

        mock_execute_spotify_api_request.assert_called_once_with(
            session_id,
            endpoint,
            request_method='GET'
        )
        self.assertIsInstance(current_user, dict)
        self.assertEqual(current_user['display_name'],'test_display_name_response')
        self.assertEqual(current_user['external_url'],'test_external_url_response')
        self.assertEqual(current_user['id'],'id_response')
        self.assertNotIn('image_url', current_user)

    @patch('playlistapp.spotifyService.util.is_spotify_authenticated')
    @patch('playlistapp.spotifyService.util.get')
    def test_get_current_user_valid_user_get_request(self,mock_get,mock_is_spotify_authenticated):
        session_id = self.user_id
        mock_is_spotify_authenticated.return_value = True
        current_user = get_current_user(session_id)
        mock_get.assert_called_once_with(
            'https://api.spotify.com/v1/me/',
            params=None,
            data=None,
            headers = {'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + self.token.access_token}
        )


class AddCustomImageToPlaylistTestCase(BaseTestCase):

    @patch('playlistapp.spotifyService.util.put')
    def test_add_custom_image_to_playlist(self, mock_put):
        session_id = self.user_id
        playlist_id = 'Playlist_ID'
        expected_endpoint = f'https://api.spotify.com/v1/playlists/{playlist_id}/images'
        expected_headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + self.token.access_token}

        image = Image.new('RGB', (100, 100), color='red')
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', prefix='test_image',delete=False)
        image.save(temp_file.name, format='JPEG')
        with open(temp_file.name, 'rb') as f:
            expected_data = base64.b64encode(f.read())

        add_custom_image_to_playlist(session_id, playlist_id, temp_file)
        mock_put.assert_called_once_with(
            expected_endpoint,
            params=None,
            data=expected_data,
            headers=expected_headers
        )

class GetArtistsTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_responses = [
            {
                'artists': {
                    'items': [
                        {
                            'name': 'Artist1',
                            'id': '123',
                            'external_urls': {'spotify': 'https://open.spotify.com/artist/123'},
                            'images': [{'url': 'https://example.com/image.jpg'}],
                        }
                    ]
                }
            },
            {
                'artists': {
                    'items': [
                        {
                            'name': 'Artist2',
                            'id': '456',
                            'external_urls': {'spotify': 'https://open.spotify.com/artist/456'},
                            'images': [{'url': 'https://example.com/image2.jpg'}],
                        }
                    ]
                }
            }
        ]
        self.expected_result = [
            {
                'name': 'Artist1',
                'id': '123',
                'external_url': 'https://open.spotify.com/artist/123',
                'image_url': 'https://example.com/image.jpg',
            },
            {
                'name': 'Artist2',
                'id': '456',
                'external_url': 'https://open.spotify.com/artist/456',
                'image_url': 'https://example.com/image2.jpg',
            },
        ]

    @patch('playlistapp.spotifyService.util.execute_spotify_api_request')
    def test_get_artists(self, mock_execute_spotify_api_request):
        session_id = self.user_id
        expected_endpoint = 'search/'
        artists_form = ['test_artist_1','test_artist_2']
        mock_execute_spotify_api_request.side_effect = self.mock_responses
        artist_data = get_artists(session_id, artists_form)
        self.assertEqual(artist_data, self.expected_result)
        mock_execute_spotify_api_request.assert_called()
        expected_calls = []
        for artist in artists_form:
            expected_params = {
                'q': artist,
                'type': 'artist',
                'limit': 1,
            }
            expected_calls.append(call(
                session_id,
                expected_endpoint,
                request_method='GET',
                params=expected_params
            ))
        mock_execute_spotify_api_request.assert_has_calls(expected_calls)

    @patch('playlistapp.spotifyService.util.get')
    def test_get_artists_get_request(self, mock_get):
        session_id = self.user_id
        expected_endpoint = 'https://api.spotify.com/v1/search/'
        expected_headers = {'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + self.token.access_token}
        artists_form = ['test_artist_1','test_artist_2']
        mock_http_responses = []
        for response_dict in self.mock_responses:
            response_str = json.dumps(response_dict)
            response = Response()
            response._content = response_str.encode('utf-8')
            response.status_code = 200
            mock_http_responses.append(response)

        mock_get.side_effect = mock_http_responses
        artist_data = get_artists(session_id, artists_form)
        self.assertEqual(artist_data, self.expected_result)
        mock_get.assert_called()
        expected_calls = []
        for artist in artists_form:
            expected_params = {
                'q': artist,
                'type': 'artist',
                'limit': 1,
            }
            expected_calls.append(call(
                expected_endpoint,
                params=expected_params,
                data=None,
                headers=expected_headers
            ))
        mock_get.assert_has_calls(expected_calls)

    @patch('playlistapp.spotifyService.util.execute_spotify_api_request')
    def test_get_artists_index_error(self, mock_execute_spotify_api_request):
        session_id = self.user_id
        artists_form = ['test_artist_1','test_artist_2']
        mock_response = {'artists': {'items': []}}
        mock_execute_spotify_api_request.return_value = mock_response
        expected_data = []
        artist_data = get_artists(session_id, artists_form)
        mock_execute_spotify_api_request.assert_called()
        self.assertEqual(artist_data, expected_data)

class GetArtistsTopTracksUrisTestCase(BaseTestCase):

    @patch('playlistapp.spotifyService.util.execute_spotify_api_request')
    def test_get_artists_top_tracks_uris(self,mock_execute_spotify_api_request):
        session_id = self.user_id
        artists_data = [{'name': 'Artist1','id': '123'}, {'name': 'Artist2','id': '456'}]
        mock_responses = [
            {'tracks': [{'uri': 'track:1:Artist1'}, {'uri': 'track:2:Artist1'}]},
            {'tracks': [{'uri': 'track:1:Artist2'}, {'uri': 'track:2:Artist2'}]}
        ]
        mock_execute_spotify_api_request.side_effect = mock_responses
        result = get_artists_top_tracks_uris(session_id, artists_data)
        expected_calls = []
        for artist in artists_data:
            artist_id = artist.get('id')
            expected_endpoint = f'artists/{artist_id}/top-tracks?market=US'
            expected_calls.append(call(
                session_id,
                expected_endpoint,
                request_method='GET'
            ))
        mock_execute_spotify_api_request.assert_has_calls(expected_calls)
        self.assertEqual(result, 'track:1:Artist1,track:2:Artist1,track:1:Artist2,track:2:Artist2')

    @patch('playlistapp.spotifyService.util.execute_spotify_api_request')
    def test_get_artists_top_tracks_uris_empty_list(self,mock_execute_spotify_api_request):
        session_id = self.user_id
        artists_data = [{'name': 'Artist1','id': '123'}, {'name': 'Artist2','id': '456'}]
        mock_responses = [
            {'tracks': [{'uri': 'track:1:Artist1'}, {'uri': 'track:2:Artist1'}]},
            {'tracks': []}
        ]
        mock_execute_spotify_api_request.side_effect = mock_responses
        result = get_artists_top_tracks_uris(session_id, artists_data)
        expected_calls = []
        for artist in artists_data:
            artist_id = artist.get('id')
            expected_endpoint = f'artists/{artist_id}/top-tracks?market=US'
            expected_calls.append(call(
                session_id,
                expected_endpoint,
                request_method='GET'
            ))
        mock_execute_spotify_api_request.assert_has_calls(expected_calls)
        self.assertEqual(result, 'track:1:Artist1,track:2:Artist1')

class AddTracksToPlaylistTestCase(BaseTestCase):

    @patch('playlistapp.spotifyService.util.execute_spotify_api_request')
    def test_add_tracks_to_playlist(self,mock_execute_spotify_api_request):
        session_id = self.user_id
        playlist_id = 'Playlist_ID'
        tracks_uris_str = 'track:1:Artist1,track:2:Artist1'
        expected_endpoint = f'playlists/{playlist_id}/tracks'
        expected_params = {
            'uris': tracks_uris_str
        }

        add_tracks_to_playlist(session_id,playlist_id,tracks_uris_str)
        mock_execute_spotify_api_request.assert_called_once_with(
            session_id,
            expected_endpoint,
            request_method='POST',
            params=expected_params
        )

    @patch('playlistapp.spotifyService.util.post')
    def test_add_tracks_to_playlist_post_request(self,mock_post):
        session_id = self.user_id
        playlist_id = 'Playlist_ID'
        tracks_uris_str = 'track:1:Artist1,track:2:Artist1'
        expected_endpoint = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
        expected_params = {
            'uris': tracks_uris_str
        }
        expected_headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + self.token.access_token}

        add_tracks_to_playlist(session_id,playlist_id,tracks_uris_str)
        mock_post.assert_called_once_with(
            expected_endpoint,
            params=expected_params,
            data=None,
            headers=expected_headers
        )

class CreateAPlayListTestCase(TestCase):

    @patch('playlistapp.spotifyService.util.get_current_user')
    @patch('playlistapp.spotifyService.util.execute_spotify_api_request')
    @patch('playlistapp.spotifyService.util.get_artists')
    @patch('playlistapp.spotifyService.util.get_artists_top_tracks_uris')
    @patch('playlistapp.spotifyService.util.add_custom_image_to_playlist')
    @patch('playlistapp.spotifyService.util.add_tracks_to_playlist')
    def test_create_a_playlist(self, mock_add_tracks_to_playlist, mock_add_custom_image_to_playlist,
                                mock_get_artists_top_tracks_uris,mock_get_artists, mock_execute_spotify_api_request,
                                mock_get_current_user):
        session_id = 'my_session_id'
        form_data = {
            'name': 'My playlist',
            'description': 'This is my playlist',
            'public': True,
            'artists': ['artist1', 'artist2'],
            'img': 'https://example.com/myimage.png'
        }
        mock_get_current_user.return_value = {'id': 'test_user_id'}
        mock_execute_spotify_api_request.return_value = {'id': 'my_playlist_id'}
        mock_get_artists_top_tracks_uris.return_value = 'uri1,uri2'
        create_a_playlist(session_id,form_data)
        mock_get_current_user.assert_called_with(session_id)
        mock_execute_spotify_api_request.assert_called_with(session_id, 'users/test_user_id/playlists', request_method='POST', 
                                          data='{"name": "My playlist", "description": "This is my playlist", "public": true}')
        mock_get_artists.assert_called_with(session_id, ['artist1', 'artist2'])
        mock_get_artists_top_tracks_uris.assert_called_with(session_id, mock_get_artists.return_value)
        mock_add_custom_image_to_playlist.assert_called_with(session_id, 'my_playlist_id', 'https://example.com/myimage.png')
        mock_add_tracks_to_playlist.assert_called_with(session_id, 'my_playlist_id', 'uri1,uri2')


class GetCurrendUsersPlaylistTestCase(BaseTestCase):

    @patch('playlistapp.spotifyService.util.is_spotify_authenticated')
    @patch('playlistapp.spotifyService.util.execute_spotify_api_request')
    def test_get_current_users_playlists(self,mock_execute_spotify_api_request,mock_is_spotify_authenticated):
        session_id = self.user_id
        expected_endpoint = 'me/playlists'
        expected_params = {
        'limit': 20
        }
        mock_is_spotify_authenticated.return_value = True
        mock_response = {
            'items': [
                {
                    'name': 'My Playlist',
                    'external_urls': {'spotify': 'https://open.spotify.com/playlist/123'},
                    'images': [{'url': 'https://example.com/image.jpg'}],
                    'id': '123'
                },
                {
                    'name': 'My Playlist2',
                    'external_urls': {'spotify': 'https://open.spotify.com/playlist2/456'},
                    'images': [{'url': 'https://example.com/image2.jpg'}],
                    'id': '456'
                }
            ]
        }
        mock_execute_spotify_api_request.return_value = mock_response
        current_users_playlists = get_current_users_playlists(session_id)
        mock_execute_spotify_api_request.assert_called_once_with(
            session_id,
            expected_endpoint,
            request_method='GET',
            params = expected_params
        )
        self.assertEqual(len(current_users_playlists), 2)
        self.assertEqual(current_users_playlists[0]['name'], 'My Playlist')
        self.assertEqual(current_users_playlists[0]['external_url'], 'https://open.spotify.com/playlist/123')
        self.assertEqual(current_users_playlists[0]['image_url'], 'https://example.com/image.jpg')
        self.assertEqual(current_users_playlists[0]['id'], '123')
        self.assertEqual(current_users_playlists[1]['name'], 'My Playlist2')
        self.assertEqual(current_users_playlists[1]['external_url'], 'https://open.spotify.com/playlist2/456')
        self.assertEqual(current_users_playlists[1]['image_url'], 'https://example.com/image2.jpg')
        self.assertEqual(current_users_playlists[1]['id'], '456')

    @patch('playlistapp.spotifyService.util.is_spotify_authenticated')
    @patch('playlistapp.spotifyService.util.execute_spotify_api_request')
    def test_get_current_users_playlists_no_image_url(self,mock_execute_spotify_api_request,mock_is_spotify_authenticated):
        session_id = self.user_id
        expected_endpoint = 'me/playlists'
        expected_params = {
        'limit': 20
        }
        mock_is_spotify_authenticated.return_value = True
        mock_response = {
            'items': [
                {
                    'name': 'My Playlist',
                    'external_urls': {'spotify': 'https://open.spotify.com/playlist/123'},
                    'images': [],
                    'id': '123'
                }
            ]
        }
        mock_execute_spotify_api_request.return_value = mock_response
        current_users_playlists = get_current_users_playlists(session_id)
        mock_execute_spotify_api_request.assert_called_once_with(
            session_id,
            expected_endpoint,
            request_method='GET',
            params = expected_params
        )
        self.assertEqual(len(current_users_playlists), 1)
        self.assertEqual(current_users_playlists[0]['name'], 'My Playlist')
        self.assertEqual(current_users_playlists[0]['external_url'], 'https://open.spotify.com/playlist/123')
        self.assertEqual(current_users_playlists[0]['id'], '123')
        self.assertNotIn('image_url', current_users_playlists)
