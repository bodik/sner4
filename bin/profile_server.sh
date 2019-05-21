#!/bin/sh
# run sner server and profile the execution

python -m profile -o /tmp/sner_server_last.profile bin/server $@

python -m cprofilev -f /tmp/sner_server_last.profile &
PID=$!
sleep 3
links http://127.0.0.1:4000
kill -TERM $PID
wait
