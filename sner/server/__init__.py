"""main application package module"""

import os

import flask.cli
from flask import Flask, render_template
from flask_debugtoolbar import DebugToolbarExtension
from flask_jsglue import JSGlue
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import generate_csrf
import yaml


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
    'SNER_AUTH_ROLES': ['user', 'operator', 'admin']
}

db = SQLAlchemy()  # pylint: disable=invalid-name
jsglue = JSGlue()  # pylint: disable=invalid-name
login_manager = LoginManager()  # pylint: disable=invalid-name
toolbar = DebugToolbarExtension()  # pylint: disable=invalid-name


def get_dotted(data, path):
    """access nested dict by dotted helper"""

    parts = path.split('.')
    if len(parts) == 1:
        return data.get(parts[0])
    if (parts[0] in data) and isinstance(data[parts[0]], dict):
        return get_dotted(data[parts[0]], '.'.join(parts[1:]))
    return None


def config_from_yaml(filename):
    """pull config variables from config file"""

    if filename and os.path.exists(filename):
        with open(filename, 'r') as ftmp:
            config_dict = yaml.safe_load(ftmp.read())
        config = {
            'SECRET_KEY': get_dotted(config_dict, 'server.secret'),
            'SQLALCHEMY_DATABASE_URI': get_dotted(config_dict, 'server.db'),
            'SNER_VAR': get_dotted(config_dict, 'server.var')}
        config = {k: v for k, v in config.items() if v is not None}
        return config

    return {}


def create_app(config_file=None, config_env='SNER_CONFIG'):
    """flask application factory"""

    app = Flask('sner.server')
    app.config.update(DEFAULT_CONFIG)  # default config
    app.config.update(config_from_yaml(config_file))  # passed from other programs, eg. tests
    app.config.update(config_from_yaml('sner.yaml'))  # easy configuration from cwd
    app.config.update(config_from_yaml(os.environ.get(config_env)))  # wsgi config

    db.init_app(app)
    jsglue.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login_route'
    login_manager.login_message = 'Not logged in'
    login_manager.login_message_category = 'warning'
    if app.config['DEBUG']:  # pragma: no cover
        toolbar.init_app(app)

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
    def format_datetime(value, fmt="%Y-%m-%dT%H:%M:%S"):  # pylint: disable=unused-variable
        """Format a datetime"""
        if value is None:
            return ""
        return value.strftime(fmt)

    # globaly enable flask_wtf csrf token helper
    # least intrusive way to pass token into every view without enforcing csrf on all routes
    app.add_template_global(name='csrf_token', f=generate_csrf)

    @app.shell_context_processor
    def make_shell_context():  # pylint: disable=unused-variable
        from sner.server.model.auth import User
        from sner.server.model.scheduler import Excl, ExclFamily, Job, Queue, Target, Task
        from sner.server.model.storage import Host, Note, Service, Vuln
        return {
            'app': app, 'db': db,
            'Excl': Excl, 'ExclFamily': ExclFamily, 'Job': Job, 'Queue': Queue, 'Target': Target, 'Task': Task,
            'Host': Host, 'Note': Note, 'Service': Service, 'Vuln': Vuln,
            'User': User}

    return app


def cli():
    """server command wrapper"""

    os.environ['FLASK_APP'] = 'sner.server'
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_RUN_PORT'] = '18000'
    os.environ['FLASK_RUN_HOST'] = '0.0.0.0'
    return flask.cli.main()
