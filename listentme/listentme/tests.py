import importlib
import os
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.password_validation import validate_password
from django.test import TestCase, LiveServerTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


class ListentmeSecretKeyTestCase(TestCase):

    def test_secret_key_strenght(self):
        SECRET_KEY = os.environ.get('SECRET_KEY')
        if not SECRET_KEY:
            raise AssertionError('SECRET_KEY not set in environment!')
        try:
            is_strong = validate_password(SECRET_KEY)
        except Exception as e:
            msg = f'Weak Secret Key {e.messages}'
            self.fail(msg)

class ListentmePostgreSQLTestCase(TestCase):

    def test_psycopg2_installed(self):
        try:
            importlib.import_module('psycopg2')
            assert True
        except ImportError:
            assert False

    def test_db_password(self):
        DB_PASSWORD = os.environ.get('DB_PASSWORD')
        if not DB_PASSWORD:
            raise AssertionError('The DB_PASSWORD variable is not set.')
        try:
            is_strong = validate_password(DB_PASSWORD)
        except Exception as e:
            msg = f'Weak Secret Key {e.messages}'
            self.fail(msg)

class ListentmeSpotifyConfigTestCase(TestCase):

    def test_spotify_variable_set_up(self):
        if not os.environ.get('CLIENT_ID'):
            raise AssertionError('The CLIENT_ID variable is not set.')
        if not os.environ.get('CLIENT_SECRET'):
            raise AssertionError('The CLIENT_SECRET variable is not set.')
        if not os.environ.get('REDIRECT_URI'):
            raise AssertionError('The REDIRECT_URI variable is not set.')
        if not  os.environ.get('BASE_URL'):
            raise AssertionError('The BASE_URL variable is not set.')

