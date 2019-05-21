#!/bin/sh
# simple cloud development helper

apt-get update
apt-get install git mc
apt-get purge joe nano pico

git clone https://gitlab.flab.cesnet.cz/bodik/sner4 /opt/sner
cd /opt/sner || exit 1
ln -s ../../bin/git_hookprecommit.sh .git/hooks/pre-commit


make install-deps
make venv
. venv/bin/activate
make test
