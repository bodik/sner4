#!/bin/sh

export FLASK_APP="sner4web"
export FLASK_ENV="development"
flask run --host 0.0.0.0 --port 18000
