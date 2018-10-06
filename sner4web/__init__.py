from flask import Flask, render_template


def create_app(config_file="sner4web.cfg"):
	app = Flask(__name__)
	app.config.from_pyfile(config_file)

	@app.route("/")
	def index():
		return render_template("index.html")

	return app
