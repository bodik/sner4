#!/bin/sh

export FLASK_APP="sner_web"
export FLASK_ENV="development"
flask run --host 0.0.0.0 --port 18000
