#!/bin/sh

BASE="$(readlink -f $(dirname $(readlink -f $0))/..)"
export SNER_CONFIG="${BASE}/sner-server.cfg"

export FLASK_APP="sner.server"
export FLASK_ENV="development"
export FLASK_RUN_PORT=18000
export FLASK_RUN_HOST='0.0.0.0'
flask run $@
