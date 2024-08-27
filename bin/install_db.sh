#!/bin/sh

apt-get -y install postgresql postgresql-contrib
systemctl start postgresql

sudo -u postgres psql -c "CREATE USER ${USER}" | true
sudo -u postgres psql -c "CREATE DATABASE sner" | true
sudo -u postgres psql -c "GRANT ALL ON SCHEMA public to ${USER}" sner | true
mkdir -p /var/lib/sner
chown www-data /var/lib/sner

sudo -u postgres psql -c "CREATE DATABASE sner_test" | true
sudo -u postgres psql -c "GRANT ALL ON SCHEMA public to ${USER}" sner_test | true
mkdir -p /tmp/sner_test_var
