"""main application package module"""

from flask import flash, Flask, render_template
from flask_debugtoolbar import DebugToolbarExtension
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import generate_csrf


db = SQLAlchemy() # pylint: disable=invalid-name
toolbar = DebugToolbarExtension() # pylint: disable=invalid-name


def create_app():
	"""flask application factory"""

	app = Flask(__name__)
	app.config.from_envvar('SNER_CONFIG')

	db.init_app(app)
	toolbar.init_app(app)

	from sner.server.controller import scheduler
	app.register_blueprint(scheduler.blueprint, url_prefix='/scheduler')
	from sner.server.controller import storage
	app.register_blueprint(storage.blueprint, url_prefix='/storage')

	from sner.server.command.db import db_command
	app.cli.add_command(db_command)
	from sner.server.command.scheduler import scheduler_command
	app.cli.add_command(scheduler_command)
	from sner.server.command.storage import storage_command
	app.cli.add_command(storage_command)

	@app.route('/')
	def index_route(): # pylint: disable=unused-variable
		flash('info', 'info')
		flash('success', 'success')
		flash('warning', 'warning')
		flash('error', 'error')
		return render_template('index.html')

	@app.template_filter('datetime')
	def format_datetime(value, fmt="%Y-%m-%dT%H:%M:%S"): # pylint: disable=unused-variable
		"""Format a datetime"""
		if value is None:
			return ""
		return value.strftime(fmt)

	# globaly enable flask_wtf csrf token helper
	# least intrusive way to pass token into every view without enforcing csrf on all routes
	app.jinja_env.globals['csrf_token'] = generate_csrf

	return app
