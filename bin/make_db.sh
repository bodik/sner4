#!/bin/sh

BASE="$(readlink -f $(dirname $(readlink -f $0))/..)"

rm -f db.sqlite3
export SNER_CONFIG="${BASE}/sner_web.cfg"
export FLASK_APP="sner_web"
flask sner_initdb
