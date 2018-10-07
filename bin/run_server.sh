#!/bin/sh

export FLASK_APP="sner4web"
export FLASK_ENV="development"
#export FLASK_RUN_HOST="0.0.0.0"
#export FLASK_RUN_PORT="18000"
flask run --host 0.0.0.0 --port 18000
