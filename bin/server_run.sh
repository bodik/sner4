#!/bin/sh

BASE="$(readlink -f $(dirname $(readlink -f $0))/..)"
export SNER_CONFIG="${BASE}/sner-server.cfg"

export FLASK_APP="sner.server"
export FLASK_ENV="development"
flask run --host 0.0.0.0 --port 18000
