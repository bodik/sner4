#!/bin/sh

apt-get -y install gcc libpq-dev python3-dev unzip

apt-get -y install python3-venv
python3 -m venv venv
. venv/bin/activate
pip install -U pip
pip install -r requirements.lock

cp -vn sner.yaml.example /etc/sner.yaml

cp extra/sner-web.service /etc/systemd/system/sner-web.service
cp extra/sner-agent@.service /etc/systemd/system/sner-agent@.service
cp extra/sner-planner.service /etc/systemd/system/sner-planner.service
systemctl daemon-reload
