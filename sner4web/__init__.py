from flask import flash, Flask, render_template


def create_app(config_file="sner4web.cfg"):
	app = Flask(__name__)
	app.config.from_pyfile(config_file)

	@app.route("/")
	def index():
		flash("info", "info")
		flash("success", "success")
		flash("warning", "warning")
		flash("error", "error")
		return render_template("index.html")

	return app
