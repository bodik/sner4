"""main application package module"""

from flask import flash, Flask, render_template
from sner.server.command.db import db_command
from sner.server.command.scheduler import scheduler_command
from sner.server.controller import scheduler
from sner.server.extensions import db, toolbar


def create_app():
	"""flask application factory"""

	app = Flask(__name__)
	app.config.from_envvar('SNER_CONFIG')

	toolbar.init_app(app)
	db.init_app(app)

	app.register_blueprint(scheduler.blueprint, url_prefix='/scheduler')

	app.cli.add_command(db_command)
	app.cli.add_command(scheduler_command)

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

	return app
