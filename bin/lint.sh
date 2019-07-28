#!/bin/sh
# development helper

python -m flake8 $@
python -m pylint $@
