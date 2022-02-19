#!/bin/sh

apt-get -y install postgresql-all
systemctl start postgresql

sudo -u postgres psql -c "CREATE DATABASE sner" | true
sudo -u postgres psql -c "CREATE USER ${USER}" | true
mkdir -p /var/lib/sner

sudo -u postgres psql -c "CREATE DATABASE sner_test" | true
sudo -u postgres psql -c "CREATE USER ${USER}" | true
mkdir -p /tmp/sner_test_var
