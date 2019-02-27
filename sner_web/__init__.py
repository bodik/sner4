"""main application package module"""

from flask import flash, Flask, render_template
from sner_web.commands import init_db, init_data
from sner_web.controller import profile, task
from sner_web.extensions import db, toolbar
from sner_web.models import Profile, Task



def create_app():
	"""flask application factory"""

	app = Flask(__name__)
	app.config.from_envvar("SNER_CONFIG")

	toolbar.init_app(app)
	db.init_app(app)

	app.register_blueprint(profile.blueprint, url_prefix="/profile")
	app.register_blueprint(task.blueprint, url_prefix="/task")

	app.cli.add_command(init_db)
	app.cli.add_command(init_data)

	@app.route("/")
	def index_route(): # pylint: disable=unused-variable
		flash("info", "info")
		flash("success", "success")
		flash("warning", "warning")
		flash("error", "error")
		return render_template("index.html")

	return app
