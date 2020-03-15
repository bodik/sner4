#!/bin/sh
# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
set -e

apt-get -y install git sudo make postgresql-all
apt-get -y install apache2 libapache2-mod-wsgi-py3

make venv
. venv/bin/activate

make install-deps

sudo -u postgres scripts/database_create.sh sner sner
sudo -u postgres psql -c "ALTER USER sner WITH ENCRYPTED PASSWORD 'password';"
mkdir -p /var/lib/sner
chown www-data /var/lib/sner

cat > /etc/sner.yaml <<_EOF_
server:
    secret: 'testsecret'
    application_root: '/sner'
    db: 'postgresql://sner:password@localhost/sner'
_EOF_
make db

cp wsgi.conf.example /etc/apache2/conf-enabled/sner-wsgi.conf
/etc/init.d/apache2 restart

curl http://localhost/sner/
