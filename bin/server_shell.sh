#!/bin/sh

BASE="$(readlink -f $(dirname $(readlink -f $0))/..)"
export SNER_CONFIG="${BASE}/sner-server.cfg"

export FLASK_APP="sner.server"
flask shell
