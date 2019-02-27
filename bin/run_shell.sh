#!/bin/sh

BASE="$(readlink -f $(dirname $(readlink -f $0))/..)"

export SNER_CONFIG="${BASE}/sner_web.cfg"
export FLASK_APP="sner_web"
flask shell
