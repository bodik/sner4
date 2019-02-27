#!/bin/sh

BASE="$(readlink -f $(dirname $(readlink -f $0))/..)"

export SNER_CONFIG="${BASE}/sner_web.cfg"
export FLASK_APP="sner_web"
export FLASK_ENV="development"
flask run --host 0.0.0.0 --port 18000
