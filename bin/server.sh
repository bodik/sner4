#!/bin/sh

export SNER_CONFIG="../../sner-server.cfg"
export FLASK_APP="sner.server"
export FLASK_ENV="development"
export FLASK_RUN_PORT=18000
export FLASK_RUN_HOST='0.0.0.0'
flask "$@"
