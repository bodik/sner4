#!/bin/sh
set -e

export SNER_CONFIG="../../sner-server.cfg"
python -m pytest $@
