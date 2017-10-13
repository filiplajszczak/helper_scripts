from unittest.mock import call, patch
import os
import tempfile
from textwrap import dedent

import pythonanywhere.django_project
from pythonanywhere.django_project import (
    start_django_project,
    update_settings_file,
    update_wsgi_file,
)


class TestStartDjangoProject:

    def test_creates_folder(self, mock_subprocess, fake_home):
        start_django_project('mydomain.com', '/path/to/virtualenv', nuke=False)
        expected_path = os.path.join(fake_home, 'mydomain.com')
        assert os.path.isdir(expected_path)


    def test_calls_startproject(self, mock_subprocess, fake_home):
        start_django_project('mydomain.com', '/path/to/virtualenv', nuke=False)
        expected_path = os.path.join(fake_home, 'mydomain.com')
        assert mock_subprocess.check_call.call_args == call([
            '/path/to/virtualenv/bin/django-admin.py',
            'startproject',
            'mysite',
            expected_path
        ])


    def test_returns_project_path(self, mock_subprocess, fake_home):
        with patch('pythonanywhere.django_project.update_settings_file'):
            response = start_django_project('mydomain.com', '/path/to/virtualenv', nuke=False)
        assert response == os.path.join(fake_home, 'mydomain.com')


    def test_nuke_option_deletes_directory_first(self, mock_subprocess, fake_home):
        domain = 'mydomain.com'
        os.mkdir(os.path.join(fake_home, domain))
        old_file = os.path.join(fake_home, domain, 'old_file.py')
        with open(old_file, 'w') as f:
            f.write('old stuff')

        start_django_project(domain, '/path/to/virtualenv', nuke=True)  # should not raise

        assert not os.path.exists(old_file)




class TestUpdateSettingsFile:

    def test_adds_STATIC_and_MEDIA_config_to_settings(self):
        test_folder = tempfile.mkdtemp()
        os.makedirs(os.path.join(test_folder, 'mysite'))
        with open(os.path.join(test_folder, 'mysite/settings.py'), 'w') as f:
            f.write(dedent(
                """
                # settings file
                STATIC_URL = '/static/'
                ALLOWED_HOSTS = []
                """
            ))

        update_settings_file('mydomain.com', test_folder)
        with open(os.path.join(test_folder, 'mysite/settings.py')) as f:
            contents = f.read()

        lines = contents.split('\n')
        assert "STATIC_URL = '/static/'" in lines
        assert "MEDIA_URL = '/media/'" in lines
        assert "STATIC_ROOT = os.path.join(BASE_DIR, 'static')" in lines
        assert "MEDIA_ROOT = os.path.join(BASE_DIR, 'media')" in lines


    def test_adds_domain_to_ALLOWED_HOSTS(self):
        test_folder = tempfile.mkdtemp()
        os.makedirs(os.path.join(test_folder, 'mysite'))
        with open(os.path.join(test_folder, 'mysite/settings.py'), 'w') as f:
            f.write(dedent(
                """
                # settings file
                STATIC_URL = '/static/'
                ALLOWED_HOSTS = []
                """
            ))

        update_settings_file('mydomain.com', test_folder)
        with open(os.path.join(test_folder, 'mysite/settings.py')) as f:
            contents = f.read()

        lines = contents.split('\n')

        assert "ALLOWED_HOSTS = ['mydomain.com']" in lines



class TestUpdateWsgiFile:

    def test_updates_wsgi_file_from_template(self):
        wsgi_file = tempfile.NamedTemporaryFile().name
        template = open(os.path.join(os.path.dirname(pythonanywhere.django_project.__file__), 'wsgi_file_template.py')).read()

        update_wsgi_file(wsgi_file, '/project/path')

        with open(wsgi_file) as f:
            contents = f.read()
        assert contents == template.format(project_path='/project/path')
