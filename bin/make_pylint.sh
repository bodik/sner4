#!/bin/sh

python3 -m pylint ${@:-sner tests}
