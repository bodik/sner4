#!/bin/sh

apt-get install python-virtualenv python3-virtualenv
virtualenv -p python3 env
. env/bin/activate

pip install -r requirements.txt
