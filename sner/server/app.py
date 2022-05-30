# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
main application package module
"""

import json
import os
import sys

import flask.cli
from flask import Flask, render_template
from flask_wtf.csrf import generate_csrf
from sqlalchemy import func

from sner.agent.modules import load_agent_plugins
from sner.lib import load_yaml
from sner.server.extensions import api, db, jsglue, migrate, login_manager, oauth, webauthn
from sner.server.parser import load_parser_plugins
from sner.server.sessions import FilesystemSessionInterface
from sner.version import __version__

# blueprints and commands
from sner.server.api.views import blueprint as api_blueprint
from sner.server.auth.views import blueprint as auth_blueprint
from sner.server.scheduler.views import blueprint as scheduler_blueprint
from sner.server.storage.views import blueprint as storage_blueprint
from sner.server.visuals.views import blueprint as visuals_blueprint

from sner.server.auth.commands import command as auth_command
from sner.server.dbx_command import command as dbx_command
from sner.server.planner.commands import command as planner_command
from sner.server.psql_command import command as psql_command
from sner.server.scheduler.commands import command as scheduler_command
from sner.server.storage.commands import command as storage_command

# shell context helpers
from sner.server.auth.models import User, WebauthnCredential
from sner.server.scheduler.models import Excl, ExclFamily, Job, Heatmap, Queue, Readynet, Target
from sner.server.storage.models import Host, Note, Service, Vuln


DEFAULT_CONFIG = {
    # flask
    'SECRET_KEY': os.urandom(32),

    # sqlalchemy
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SQLALCHEMY_DATABASE_URI': 'postgresql:///sner',
    'SQLALCHEMY_ECHO': False,

    # sner-web
    'SNER_VAR': '/var/lib/sner',
    'SNER_AUTH_ROLES': ['admin', 'agent', 'operator', 'user'],
    'SNER_SESSION_IDLETIME': 36000,
    'SNER_TAGS_HOST': ['reviewed'],
    'SNER_TAGS_VULN': ['info', 'report', 'todo', 'falsepositive'],
    'SNER_TAGS_ANNOTATE': ['sslhell'],
    'SNER_TRIM_REPORT_CELLS': 65000,

    # other sner subsystems
    'SNER_PLANNER': {},
    'SNER_VULNSEARCH': {},
    'SNER_HEATMAP_HOT_LEVEL': 0,

    # smorest api
    'API_TITLE': 'sner4 api',
    'API_VERSION': 'vX',
    'OPENAPI_VERSION': '3.0.2',
    'OPENAPI_URL_PREFIX': '/api/doc',
    'OPENAPI_SWAGGER_UI_PATH': '/swagger',
    'OPENAPI_SWAGGER_UI_URL': "https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
    # https://github.com/marshmallow-code/flask-smorest/issues/36
    # https://swagger.io/docs/specification/authentication/bearer-authentication/
    'API_SPEC_OPTIONS': {
        'components': {
            'securitySchemes': {
                'ApiKeyAuth': {'type': 'apiKey', 'in': 'header', 'name': 'X-API-KEY'}
            }
        },
        'security': [
            {'ApiKeyAuth': []}
        ]
    },

    # oauth oidc
    'OIDC_NAME': None,
    # 'OIDC_DEFAULT_METADATA': 'https://URL/.well-known/openid-configuration',
    # 'OIDC_DEFAULT_CLIENT_ID': '',
    # 'OIDC_DEFAULT_CLIENT_SECRET': ''
}


def config_from_yaml(filename):
    """pull config variables from config file"""

    config_dict = load_yaml(filename)
    config = {k.upper(): v for k, v in config_dict.get('server', {}).items()}
    if 'planner' in config_dict:
        config['SNER_PLANNER'] = config_dict['planner']
    return config


def create_app(config_file='/etc/sner.yaml', config_env='SNER_CONFIG'):
    """flask application factory"""

    app = Flask('sner.server')
    app.config.update(DEFAULT_CONFIG)  # default config
    app.config.update(config_from_yaml(config_file))  # service configuration
    app.config.update(config_from_yaml(os.environ.get(config_env)))  # wsgi/container config

    app.session_interface = FilesystemSessionInterface(os.path.join(app.config['SNER_VAR'], 'sessions'), app.config['SNER_SESSION_IDLETIME'])

    db.init_app(app)
    jsglue.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login_route'
    login_manager.login_message = 'Not logged in'
    login_manager.login_message_category = 'warning'
    migrate.init_app(app, db)
    oauth.init_app(app)
    if app.config['OIDC_NAME']:
        oauth.register(
            name=app.config['OIDC_NAME'],
            server_metadata_url=app.config[f'{app.config["OIDC_NAME"]}_METADATA'],
            client_kwargs={'scope': 'openid email profile'}
        )
    webauthn.init_app(app)

    # load sner.plugin components
    load_agent_plugins()
    load_parser_plugins()

    # initialize api blueprint; as side-effect overrides error handler
    api.init_app(app)
    api.register_blueprint(api_blueprint, url_prefix='/api')

    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(scheduler_blueprint, url_prefix='/scheduler')
    app.register_blueprint(storage_blueprint, url_prefix='/storage')
    app.register_blueprint(visuals_blueprint, url_prefix='/visuals')

    app.cli.add_command(auth_command)
    app.cli.add_command(dbx_command)
    app.cli.add_command(planner_command)
    app.cli.add_command(psql_command)
    app.cli.add_command(scheduler_command)
    app.cli.add_command(storage_command)

    @app.template_filter('datetime')
    def format_datetime(value, fmt='%Y-%m-%dT%H:%M:%S'):  # pylint: disable=unused-variable
        """Format a datetime"""
        if value is None:
            return ''
        return value.strftime(fmt)

    @app.template_filter('json_indent')
    def json_indent(data):  # pylint: disable=unused-variable
        """parse and format json"""
        try:
            return json.dumps(json.loads(data), sort_keys=True, indent=4)
        except ValueError:
            return data

    # globaly enable flask_wtf csrf token helper
    # least intrusive way to pass token into every view without enforcing csrf on all routes
    app.add_template_global(name='csrf_token', f=generate_csrf)

    @app.shell_context_processor
    def make_shell_context():  # pylint: disable=unused-variable
        return {
            'app': app, 'db': db, 'func': func,
            'Excl': Excl, 'ExclFamily': ExclFamily, 'Heatmap': Heatmap, 'Job': Job, 'Queue': Queue, 'Readynet': Readynet, 'Target': Target,
            'Host': Host, 'Note': Note, 'Service': Service, 'Vuln': Vuln,
            'User': User, 'WebauthnCredential': WebauthnCredential
        }

    @app.route('/')
    def index_route():  # pylint: disable=unused-variable
        return render_template('index.html')

    return app


def cli():
    """server command wrapper"""

    if '--version' in sys.argv:
        print(f'Sner {__version__}')
    if '--debug' in sys.argv:
        os.environ['FLASK_ENV'] = 'development'
        sys.argv.remove('--debug')
    os.environ['FLASK_APP'] = 'sner.server.app'
    os.environ['FLASK_RUN_PORT'] = '18000'
    os.environ['FLASK_RUN_HOST'] = '0.0.0.0'
    return flask.cli.main()
