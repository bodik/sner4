# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
main application package module
"""

import os
import sys

import flask.cli
from flask import Flask, render_template
from flask_jsglue import JSGlue
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import generate_csrf

from sner.lib import get_dotted, load_yaml
from sner.server.wrapped_fido2_server import WrappedFido2Server
from sner.server.sessions import FilesystemSessionInterface
from sner.version import __version__


DEFAULT_CONFIG = {
    # flask
    'SECRET_KEY': os.urandom(32),

    # debug toolbar
    'DEBUG_TB_INTERCEPT_REDIRECTS': False,

    # sqlalchemy
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SQLALCHEMY_DATABASE_URI': 'postgresql:///sner',
    'SQLALCHEMY_ECHO': False,

    'SNER_VAR': '/var/sner',
    'SNER_AUTH_ROLES': ['agent', 'user', 'operator', 'admin']
}

db = SQLAlchemy()  # pylint: disable=invalid-name
jsglue = JSGlue()  # pylint: disable=invalid-name
login_manager = LoginManager()  # pylint: disable=invalid-name
webauthn = WrappedFido2Server()  # pylint: disable=invalid-name


def config_from_yaml(filename):
    """pull config variables from config file"""

    config_dict = load_yaml(filename)
    config = {
        'SECRET_KEY': get_dotted(config_dict, 'server.secret'),
        'SQLALCHEMY_DATABASE_URI': get_dotted(config_dict, 'server.db'),
        'SNER_VAR': get_dotted(config_dict, 'server.var')}
    return {k: v for k, v in config.items() if v is not None}


def create_app(config_file=None, config_env='SNER_CONFIG'):
    """flask application factory"""

    app = Flask('sner.server')
    app.config.update(DEFAULT_CONFIG)  # default config
    app.config.update(config_from_yaml(config_file))  # passed from other programs, eg. tests
    app.config.update(config_from_yaml('sner.yaml'))  # easy configuration from cwd
    app.config.update(config_from_yaml(os.environ.get(config_env)))  # wsgi config

    app.session_interface = FilesystemSessionInterface(os.path.join(app.config['SNER_VAR'], 'sessions'))

    db.init_app(app)
    jsglue.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login_route'
    login_manager.login_message = 'Not logged in'
    login_manager.login_message_category = 'warning'
    webauthn.init_app(app)

    from sner.server.controller import api
    app.register_blueprint(api.blueprint, url_prefix='/api')
    from sner.server.controller import auth
    app.register_blueprint(auth.blueprint, url_prefix='/auth')
    from sner.server.controller import scheduler
    app.register_blueprint(scheduler.blueprint, url_prefix='/scheduler')
    from sner.server.controller import storage
    app.register_blueprint(storage.blueprint, url_prefix='/storage')

    from sner.server.command.auth import auth_command
    app.cli.add_command(auth_command)
    from sner.server.command.db import db_command
    app.cli.add_command(db_command)
    from sner.server.command.scheduler import scheduler_command
    app.cli.add_command(scheduler_command)
    from sner.server.command.storage import storage_command
    app.cli.add_command(storage_command)

    @app.route('/')
    def index_route():  # pylint: disable=unused-variable
        return render_template('index.html')

    @app.template_filter('datetime')
    def format_datetime(value, fmt='%Y-%m-%dT%H:%M:%S'):  # pylint: disable=unused-variable
        """Format a datetime"""
        if value is None:
            return ''
        return value.strftime(fmt)

    # globaly enable flask_wtf csrf token helper
    # least intrusive way to pass token into every view without enforcing csrf on all routes
    app.add_template_global(name='csrf_token', f=generate_csrf)

    @app.shell_context_processor
    def make_shell_context():  # pylint: disable=unused-variable
        from sner.server.model.auth import User, WebauthnCredential
        from sner.server.model.scheduler import Excl, ExclFamily, Job, Queue, Target, Task
        from sner.server.model.storage import Host, Note, Service, Vuln
        return {
            'app': app, 'db': db,
            'Excl': Excl, 'ExclFamily': ExclFamily, 'Job': Job, 'Queue': Queue, 'Target': Target, 'Task': Task,
            'Host': Host, 'Note': Note, 'Service': Service, 'Vuln': Vuln,
            'User': User, 'WebauthnCredential': WebauthnCredential}

    return app


def cli():
    """server command wrapper"""

    if '--version' in sys.argv:
        print('Sner %s' % __version__)
    os.environ['FLASK_APP'] = 'sner.server'
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_RUN_PORT'] = '18000'
    os.environ['FLASK_RUN_HOST'] = '0.0.0.0'
    return flask.cli.main()
