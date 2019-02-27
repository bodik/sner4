#!/bin/sh

BASE="$(readlink -f $(dirname $(readlink -f $0))/..)"
PYTHONPATH=${BASE} python sner/agent/agent.py $@
