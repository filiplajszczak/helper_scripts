from unittest.mock import call, patch, Mock
from pathlib import Path
import tempfile
from textwrap import dedent
import pytest

import pythonanywhere.django_project
from pythonanywhere.django_project import DjangoProject
from pythonanywhere.exceptions import SanityException
from pythonanywhere.api import Webapp
from pythonanywhere.virtualenvs import virtualenv_path



class TestDjangoProject:

    def test_project_path(self, fake_home):
        project = DjangoProject('mydomain.com')
        assert project.project_path == fake_home / 'mydomain.com'


    def test_wsgi_file_path(self, fake_home):
        project = DjangoProject('mydomain.com')
        assert project.wsgi_file_path == '/var/www/mydomain_com_wsgi.py'


    def test_webapp(self, fake_home):
        project = DjangoProject('mydomain.com')
        assert project.webapp == Webapp('mydomain.com')


    def test_virtualenv_path(self, fake_home):
        project = DjangoProject('mydomain.com')
        assert project.virtualenv_path == virtualenv_path('mydomain.com')


class TestSanityChecks:

    def test_calls_webapp_sanity_checks(self, fake_home):
        project = DjangoProject('mydomain.com')
        project.webapp.sanity_checks = Mock()
        project.sanity_checks(nuke='nuke.option')
        assert project.webapp.sanity_checks.call_args == call(nuke='nuke.option')


    def test_raises_if_virtualenv_exists(self, fake_home, virtualenvs_folder):
        project = DjangoProject('mydomain.com')
        project.webapp.sanity_checks = Mock()
        project.virtualenv_path.mkdir()

        with pytest.raises(SanityException) as e:
            project.sanity_checks(nuke=False)

        assert "You already have a virtualenv for mydomain.com" in str(e.value)
        assert "nuke" in str(e.value)


    def test_raises_if_project_path_exists(self, fake_home, virtualenvs_folder):
        project = DjangoProject('mydomain.com')
        project.webapp.sanity_checks = Mock()
        project.project_path.mkdir()

        with pytest.raises(SanityException) as e:
            project.sanity_checks(nuke=False)

        expected_msg = f"You already have a project folder at {fake_home}/mydomain.com"
        assert expected_msg in str(e.value)
        assert "nuke" in str(e.value)


    def test_nuke_option_overrides_directory_checks(self, fake_home, virtualenvs_folder):
        project = DjangoProject('mydomain.com')
        project.webapp.sanity_checks = Mock()
        project.project_path.mkdir()
        project.virtualenv_path.mkdir()

        project.sanity_checks(nuke=True)  # should not raise



class TestCreateVirtualenv:

    def test_calls_create_virtualenv(self):
        project = DjangoProject('mydomain.com')
        with patch('pythonanywhere.django_project.create_virtualenv') as mock_create_virtualenv:
            project.create_virtualenv('python.version', 'django.version', nuke='nuke option')
        assert mock_create_virtualenv.call_args == call(
            project.domain, 'python.version', 'django==django.version', nuke='nuke option'
        )


    def test_special_cases_latest_django_version(self):
        project = DjangoProject('mydomain.com')
        with patch('pythonanywhere.django_project.create_virtualenv') as mock_create_virtualenv:
            project.create_virtualenv('python.version', django_version='latest', nuke='nuke option')
        assert mock_create_virtualenv.call_args == call(
            project.domain, 'python.version', 'django', nuke='nuke option'
        )


    def test_sets_virtualenv_attribute(self):
        project = DjangoProject('mydomain.com')
        with patch('pythonanywhere.django_project.create_virtualenv') as mock_create_virtualenv:
            project.create_virtualenv('python.version', django_version='django.version', nuke='nuke option')
        assert project.virtualenv_path == mock_create_virtualenv.return_value


    def test_sets_python_version_attribute(self):
        project = DjangoProject('mydomain.com')
        with patch('pythonanywhere.django_project.create_virtualenv'):
            project.create_virtualenv('python.version', django_version='django.version', nuke='nuke option')
        assert project.python_version == 'python.version'



class TestRunStartproject:

    def test_creates_folder(self, mock_subprocess, fake_home):
        project = DjangoProject('mydomain.com')
        project.virtualenv_path = '/path/to/virtualenv'
        project.run_startproject(nuke=False)
        assert (fake_home / 'mydomain.com').is_dir()


    def test_calls_startproject(self, mock_subprocess, fake_home):
        project = DjangoProject('mydomain.com')
        project.virtualenv_path = '/path/to/virtualenv'
        project.run_startproject(nuke=False)
        assert mock_subprocess.check_call.call_args == call([
            Path('/path/to/virtualenv/bin/django-admin.py'),
            'startproject',
            'mysite',
            fake_home / 'mydomain.com',
        ])


    def test_nuke_option_deletes_directory_first(self, mock_subprocess, fake_home):
        project = DjangoProject('mydomain.com')
        project.virtualenv_path = '/path/to/virtualenv'
        (fake_home / project.domain).mkdir()
        old_file = fake_home / project.domain / 'old_file.py'
        with open(old_file, 'w') as f:
            f.write('old stuff')

        project.run_startproject(nuke=True)  # should not raise

        assert not old_file.exists()



class TestUpdateSettingsFile:

    def test_adds_STATIC_and_MEDIA_config_to_settings(self):
        project = DjangoProject('mydomain.com')
        project.project_path = Path(tempfile.mkdtemp())
        (project.project_path / 'mysite').mkdir(parents=True)
        with open(project.project_path / 'mysite/settings.py', 'w') as f:
            f.write(dedent(
                """
                # settings file
                STATIC_URL = '/static/'
                ALLOWED_HOSTS = []
                """
            ))

        project.update_settings_file()

        with open(project.project_path / 'mysite/settings.py') as f:
            contents = f.read()

        lines = contents.split('\n')
        assert "STATIC_URL = '/static/'" in lines
        assert "MEDIA_URL = '/media/'" in lines
        assert "STATIC_ROOT = os.path.join(BASE_DIR, 'static')" in lines
        assert "MEDIA_ROOT = os.path.join(BASE_DIR, 'media')" in lines


    def test_adds_domain_to_ALLOWED_HOSTS(self):
        project = DjangoProject('mydomain.com')
        project.project_path = Path(tempfile.mkdtemp())
        (project.project_path / 'mysite').mkdir(parents=True)
        with open(project.project_path / 'mysite/settings.py', 'w') as f:
            f.write(dedent(
                """
                # settings file
                STATIC_URL = '/static/'
                ALLOWED_HOSTS = []
                """
            ))

        project.update_settings_file()

        with open(project.project_path / 'mysite/settings.py') as f:
            contents = f.read()

        lines = contents.split('\n')

        assert "ALLOWED_HOSTS = ['mydomain.com']" in lines



class TestRunCollectStatic:

    def test_runs_manage_py_in_correct_virtualenv(self, mock_subprocess, fake_home):
        project = DjangoProject('mydomain.com')
        project.virtualenv_path = '/path/to/virtualenv'
        project.run_collectstatic()
        assert mock_subprocess.check_call.call_args == call([
            Path(project.virtualenv_path) / 'bin/python', project.project_path / 'manage.py', 'collectstatic', '--noinput'
        ])



class TestUpdateWsgiFile:

    def test_updates_wsgi_file_from_template(self):
        project = DjangoProject('mydomain.com')
        project.wsgi_file_path = tempfile.NamedTemporaryFile().name
        template = open(Path(pythonanywhere.django_project.__file__).parent / 'wsgi_file_template.py').read()

        project.update_wsgi_file()

        with open(project.wsgi_file_path) as f:
            contents = f.read()
        assert contents == template.format(project_path=project.project_path)



class TestCreateWebapp:

    def test_calls_webapp_create(self):
        project = DjangoProject('mydomain.com')
        project.webapp.create = Mock()
        project.python_version = 'python.version'

        project.create_webapp(nuke='nuke option')
        assert project.webapp.create.call_args == call(
            'python.version', project.virtualenv_path, project.project_path, nuke='nuke option'
        )



class TestAddStaticFilesMappings:

    def test_calls_webapp_add_default_static_files_mappings(self):
        project = DjangoProject('mydomain.com')
        project.webapp.add_default_static_files_mappings = Mock()
        project.add_static_file_mappings()
        assert project.webapp.add_default_static_files_mappings.call_args == call(
            project.project_path,
        )

