#!/bin/sh

export SNER_CONFIG="../../sner-server.cfg"
export FLASK_APP="sner.server"
export FLASK_ENV="development"
export FLASK_RUN_PORT=18000
export FLASK_RUN_HOST='0.0.0.0'
python -m profile -o /tmp/sner_server_last.profile env/bin/flask "$@"

python -m cprofilev -f /tmp/sner_server_last.profile &
PID=$!
sleep 3
links http://127.0.0.1:4000
kill -TERM $PID
wait
