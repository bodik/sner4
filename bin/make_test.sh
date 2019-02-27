#!/bin/sh

BASE="$(dirname $(readlink -f $0))/.."

python -m pytest tests $@
