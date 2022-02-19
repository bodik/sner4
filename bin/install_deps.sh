#!/bin/sh

apt-get -y install gcc libpq-dev python3-dev unzip

apt-get -y install python3-venv
python3 -m venv venv
. venv/bin/activate
pip install -U pip
pip install -r requirements.lock
