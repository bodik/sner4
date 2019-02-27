#!/bin/sh

BASE="$(readlink -f $(dirname $(readlink -f $0))/..)"

export SNER_CONFIG="${BASE}/sner_web.cfg"
python -m pytest --rootdir=${BASE}/sner_web/tests -p no:cacheprovider $@
