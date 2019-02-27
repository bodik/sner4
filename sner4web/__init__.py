from flask import flash, Flask, render_template
from sner4web.commands import initdb
from sner4web.controller import task
from sner4web.extensions import db, toolbar
from sner4web.models import Task



def create_app(config_file="sner4web.cfg"):
	app = Flask(__name__)
	app.config.from_pyfile(config_file)

	toolbar.init_app(app)
	db.init_app(app)

	app.register_blueprint(task.blueprint, url_prefix="/task")

	app.cli.add_command(initdb)

	@app.route("/")
	def index():
		flash("info", "info")
		flash("success", "success")
		flash("warning", "warning")
		flash("error", "error")
		return render_template("index.html")

	return app
