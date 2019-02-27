#!/bin/sh

BASE="$(readlink -f $(dirname $(readlink -f $0))/..)"
export SNER_CONFIG="${BASE}/sner-server.cfg"

python -m pytest -p no:cacheprovider $@
