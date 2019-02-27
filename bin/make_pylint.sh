#!/bin/sh

BASE="$(dirname $(readlink -f $0))/.."

python3 -m pylint --rcfile=${BASE}/.pylintrc ${@:-sner_web}
